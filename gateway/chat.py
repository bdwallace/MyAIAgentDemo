"""聊天 SSE：落库短时记忆 → 跑 LangGraph → 把事件译成 data 行。"""

from __future__ import annotations

import asyncio
import json
import uuid

from django.http import JsonResponse, StreamingHttpResponse
from langchain_core.messages import HumanMessage

from config import settings
from data.db import add_message, load_messages
from data.memory import list_memories
from data.rag import list_documents

# conversation_id -> 取消事件。终止按钮 / 客户端断开时 set。
_runs: dict[str, asyncio.Event] = {}


def cancel_run(conversation_id: str) -> bool:
    stop = _runs.get(conversation_id)
    if stop is None:
        return False
    stop.set()
    return True


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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


async def api_stop(request, conversation_id: str):
    return JsonResponse({"ok": True, "stopped": cancel_run(conversation_id)})


async def api_chat(request):
    """一次发送的入口：落库短时记忆 → 跑 LangGraph → 把事件译成 SSE。"""
    raw = request.body
    try:
        body = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON 无效"}, status=400)

    text = (body.get("message") or "").strip()
    if not text:
        return JsonResponse({"detail": "消息不能为空"}, status=400)
    from model.llm import llm_configured

    if not llm_configured():
        return JsonResponse(
            {"detail": "云端模型需要 LLM_API_KEY；本地模型请把 LLM_BASE_URL 指到本机服务"},
            status=400,
        )

    conversation_id = body.get("conversation_id") or uuid.uuid4().hex
    add_message(conversation_id, "user", text)

    async def stream():
        """SSE 生成器：一边跑 LangGraph，一边把内部事件翻译成前端能画的 data 行。

        produce() 把图事件丢进 queue；主循环每 0.25s 醒一次，看取消再取 queue。
        """
        from runtime.graph import GRAPH, to_lc_messages

        cancel = asyncio.Event()
        _runs[conversation_id] = cancel
        yield _sse({"type": "conversation", "id": conversation_id})
        yield _sse({"type": "status", "content": "模型正在生成，CPU 推理可能要几分钟，请不要刷新。\n"})
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
            try:
                async for event in GRAPH.astream_events(
                    {"messages": history},
                    version="v2",
                    config={"recursion_limit": settings.graph_recursion_limit},
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
                if cancel.is_set():
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

                if kind_name == "on_chat_model_stream":
                    for piece in _iter_text_pieces(event):
                        collected.append(piece)
                        yield _sse({"type": "text", "content": piece})

                elif kind_name == "on_chain_end" and name == "reason":
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
                    if name == "ingest_doc":
                        yield _sse({"type": "documents", "items": list_documents()})

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

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
