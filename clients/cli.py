"""终端客户端。和网页走同一套 /api/chat SSE。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clients.api import AgentClient


def _print(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def _print_health(health: dict) -> None:
    print(
        "PG {postgres}  Redis {redis}  Celery {celery}  Jail {jail}".format(
            postgres="ok" if health.get("postgres") else "down",
            redis="ok" if health.get("redis") else "down",
            celery="ok" if health.get("celery") else "down",
            jail="ok" if (health.get("sandbox") or {}).get("ok") else "down",
        )
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help"}:
        print("用法: python -m clients.cli [--health]")
        print("环境变量 AGENT_URL 默认 http://127.0.0.1:8080")
        print("会话内命令: /new  /health  /quit")
        return 0
    client = AgentClient(client="cli")
    try:
        health = client.health()
    except Exception as exc:
        print(f"连不上 Gateway（{client.base}）。先运行 python run.py\n{exc}")
        return 1
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        print(f"{client.base}  {health.get('model') or '?'}")
        _print_health(health)
        ids = [c.get("id") for c in (health.get("clients") or [])]
        print("clients:", ", ".join(ids) if ids else "(无)")
        return 0
    model = health.get("model") or "?"
    print(f"MyAiAgent CLI · {model} · {client.base}")
    print("回车发送。/new 新对话  /quit 退出  /health 状态")
    conversation_id: str | None = None
    while True:
        try:
            line = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return 0
        if not line:
            continue
        if line in {"/quit", "/exit", "/q"}:
            print("再见。")
            return 0
        if line == "/new":
            conversation_id = None
            print("已开新对话。")
            continue
        if line == "/health":
            _print_health(client.health())
            continue
        if line == "/help":
            print("/new  /health  /quit")
            continue
        print("A> ", end="")
        try:
            for ev in client.chat(line, conversation_id):
                kind = ev.get("type")
                if kind == "conversation":
                    conversation_id = ev.get("id")
                elif kind == "text":
                    _print(ev.get("content") or "")
                elif kind == "tool_start":
                    _print(f"\n[{ev.get('name')} 执行中]")
                elif kind == "tool_end":
                    out = (ev.get("output") or "").strip().splitlines()
                    brief = out[0][:80] if out else "完成"
                    _print(f"\n[{ev.get('name')} {brief}]\n")
                elif kind == "error":
                    _print(f"\n错误：{ev.get('message')}")
                elif kind in {"done", "stopped"}:
                    _print("\n")
        except KeyboardInterrupt:
            if conversation_id:
                try:
                    client.stop(conversation_id)
                except Exception:
                    pass
            print("\n已终止。")
        except Exception as exc:
            print(f"\n请求失败：{exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
