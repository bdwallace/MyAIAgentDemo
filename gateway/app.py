"""Agent Gateway · V0 用 FastAPI 临时代替。V2 会换成 Django + DRF。

职责：Session（对话 id）+ Streaming（SSE）+ 把请求交给 Runtime。
Auth / 多端路由以后再加。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from config import ROOT_DIR, settings
from data.db import (
    add_message,
    delete_conversation,
    init_db,
    list_conversations,
    load_messages,
    ping,
)
from data.memory import delete_memory, list_memories, memory_count

# conversation_id -> 取消事件。终止按钮 / 客户端断开时 set。
_runs: dict[str, asyncio.Event] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
        ping()
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL 连不上。先执行: docker compose up -d"
        ) from exc
    yield


app = FastAPI(title="MyAiAgent Gateway V0.5", lifespan=lifespan)
CLIENT_DIR = ROOT_DIR / "clients" / "web"
app.mount("/static", StaticFiles(directory=CLIENT_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/")
async def index():
    return FileResponse(CLIENT_DIR / "index.html")


@app.get("/api/health")
async def health():
    from model.llm import inspect_llm

    db_ok = False
    try:
        db_ok = ping()
    except Exception:
        db_ok = False
    llm = inspect_llm()
    from tools import ALL_TOOLS

    return {
        "ok": db_ok and llm["ready"],
        "postgres": db_ok,
        "llm": llm,
        "has_api_key": True if llm["local"] else bool(settings.llm_api_key),
        "model": settings.llm_model,
        "tools": [t.name for t in ALL_TOOLS],
        "memories": memory_count(),
    }


@app.get("/api/conversations")
async def api_conversations():
    return list_conversations()


@app.get("/api/conversations/{conversation_id}/messages")
async def api_messages(conversation_id: str):
    return load_messages(conversation_id, limit=200)


@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: str):
    stop = _runs.get(conversation_id)
    if stop is not None:
        stop.set()
    if not delete_conversation(conversation_id):
        raise HTTPException(404, "会话不存在")
    return {"ok": True}


@app.get("/api/memories")
async def api_memories():
    return list_memories()


@app.delete("/api/memories/{memory_id}")
async def api_delete_memory(memory_id: int):
    if not delete_memory(memory_id):
        raise HTTPException(404, "记忆不存在")
    return {"ok": True}


@app.post("/api/conversations/{conversation_id}/stop")
async def api_stop(conversation_id: str):
    stop = _runs.get(conversation_id)
    if stop is None:
        return {"ok": True, "stopped": False}
    stop.set()
    return {"ok": True, "stopped": True}


def _iter_text_pieces(event: dict) -> list[str]:
    data = event.get("data") or {}
    chunk = data.get("chunk")
    piece = getattr(chunk, "content", None) if chunk is not None else None
    if isinstance(piece, str) and piece:
        return [piece]
    out: list[str] = []
    if isinstance(piece, list):
        for block in piece:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text") or ""
                if t:
                    out.append(t)
    return out


@app.post("/api/chat")
async def api_chat(req: ChatRequest, request: Request):
    """一次发送的入口：落库短时记忆 → 跑 LangGraph → 把事件译成 SSE。

    事件类型见 docs/请求流程.md。页面先乐观插入气泡，真正的字来自 type=text。
    """
    text = req.message.strip()
    if not text:
        raise HTTPException(400, "消息不能为空")
    from model.llm import llm_configured

    if not llm_configured():
        raise HTTPException(400, "云端模型需要 LLM_API_KEY；本地模型请把 LLM_BASE_URL 指到本机服务")

    conversation_id = req.conversation_id or uuid.uuid4().hex
    add_message(conversation_id, "user", text)  # 短时记忆；长期记忆不在这里写

    async def stream():
        """SSE 生成器：一边跑 LangGraph，一边把内部事件翻译成前端能画的 data 行。

        为什么是嵌套函数
            FastAPI 的 StreamingResponse 要一个 async generator。外层 api_chat
            已经落好用户消息，这里只负责「跑图 + 推流」。conversation_id / text
            从闭包捕获。

        为什么拆成 produce() + 主循环
            GRAPH.astream_events 是长时间阻塞的 async for。如果直接在这个
            for 里 yield SSE，用户点「终止」或关掉标签页时，要等当前 LLM
            chunk 才有机会检查取消。所以：
              produce()  —— 后台 task，只负责把图事件丢进 queue
              主循环     —— 每 0.25s 醒一次，看取消、看断连、再取 queue
            queue 里的三元组：("event", langgraph事件) / ("end", None) / ("error", 异常)

        取消怎么生效
            终止按钮 POST /stop，或浏览器断开，都会 set cancel。
            主循环发现后 cancel producer；produce 下一圈 astream 也会 break。
            _runs[conversation_id] 让 /stop 能找到这个 Event。

        推给浏览器的 type（每个 yield 一行 SSE）
            conversation  会话 id（新对话时前端要先存下来）
            status        占位文案，等第一个 token 到来会清掉
            text          模型流式输出的一小段字
            tool_start    某个工具开始跑
            tool_end      工具返回（截断到 4000 字）
            memories      remember/forget 后整表刷新侧栏
            done/stopped  正常结束 / 被终止
            error         跑图抛错

        collected vs last_ai
            collected 拼所有流式 token，作为最终落库文本。
            last_ai 是 reason 节点整段输出的备份：本地模型有时不推
            on_chat_model_stream，图结束时用 last_ai 补一条 text。

        结束时
            把助手全文写入 messages（短时记忆）。finally 里无论成败都
            停掉 producer、从 _runs 摘掉，避免泄漏和「终止」点到幽灵任务。
        """
        from runtime.graph import GRAPH, to_lc_messages

        cancel = asyncio.Event()
        _runs[conversation_id] = cancel
        yield _sse({"type": "conversation", "id": conversation_id})
        yield _sse({"type": "status", "content": "模型正在生成，CPU 推理可能要几分钟，请不要刷新。\n"})
        # 图的输入只有会话历史；System Prompt 由 reason 每轮自己拼
        history = to_lc_messages(
            load_messages(conversation_id, limit=settings.max_history_messages)
        )
        if not history or not isinstance(history[-1], HumanMessage):
            history.append(HumanMessage(content=text))

        collected: list[str] = []
        last_ai = ""
        stopped = False
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

        async def produce() -> None:
            # 独立 task：边跑图边把 LangGraph 事件丢进 queue，主循环才能随时响应取消
            try:
                async for event in GRAPH.astream_events(
                    {"messages": history},
                    version="v2",
                ):
                    if cancel.is_set():
                        break
                    await queue.put(("event", event))
                await queue.put(("end", None))
            except asyncio.CancelledError:
                await queue.put(("end", None))
                raise
            except Exception as exc:
                await queue.put(("error", exc))

        producer = asyncio.create_task(produce())
        try:
            while True:
                if cancel.is_set() or await request.is_disconnected():
                    stopped = True
                    cancel.set()
                    producer.cancel()
                    break
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

                if kind == "end":
                    break
                if kind == "error":
                    raise payload  # type: ignore[misc]
                if not isinstance(payload, dict):
                    continue

                event = payload
                kind_name = event.get("event")
                name = event.get("name") or ""
                data = event.get("data") or {}

                # LangGraph 事件 → 前端 SSE。前端按 type 改气泡 / 侧栏
                if kind_name == "on_chat_model_stream":
                    for piece in _iter_text_pieces(event):
                        collected.append(piece)
                        yield _sse({"type": "text", "content": piece})

                elif kind_name == "on_chain_end" and name == "reason":
                    # 无流式 token 时（部分本地模型）用完整 AI 文本兜底
                    output = data.get("output") or {}
                    msgs = output.get("messages") or []
                    if msgs:
                        content = getattr(msgs[-1], "content", "")
                        if isinstance(content, str) and content.strip():
                            last_ai = content.strip()

                elif kind_name == "on_tool_start":
                    yield _sse({"type": "tool_start", "name": name, "input": data.get("input")})

                elif kind_name == "on_tool_end":
                    yield _sse(
                        {
                            "type": "tool_end",
                            "name": name,
                            "output": str(data.get("output"))[:4000],
                        }
                    )
                    if name in {"remember", "forget"}:
                        yield _sse({"type": "memories", "items": list_memories()})

            # 图结束：把完整回答写入 messages，下次短时窗口能看见
            answer = "".join(collected).strip() or last_ai
            if answer:
                add_message(conversation_id, "assistant", answer, create=False)
                if not collected:
                    yield _sse({"type": "text", "content": answer})
            yield _sse({"type": "stopped" if stopped else "done"})
        except asyncio.CancelledError:
            answer = "".join(collected).strip() or last_ai
            if answer:
                add_message(conversation_id, "assistant", answer, create=False)
            raise
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
        finally:
            cancel.set()
            if not producer.done():
                producer.cancel()
                try:
                    await producer
                except (asyncio.CancelledError, Exception):
                    pass
            _runs.pop(conversation_id, None)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
