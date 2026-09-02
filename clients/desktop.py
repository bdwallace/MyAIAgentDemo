"""桌面窗：用系统 WebView 打开同一套 Web 页。没装 pywebview 时退回浏览器。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clients.api import AgentClient


def main() -> int:
    client = AgentClient(client="desktop")
    try:
        client.health()
    except Exception as exc:
        print(f"连不上 Gateway（{client.base}）。先运行 python run.py\n{exc}")
        return 1
    try:
        import webview
    except ImportError:
        import webbrowser

        print("未安装 pywebview，改用系统浏览器。可执行: pip install pywebview")
        webbrowser.open(client.base)
        return 0
    webview.create_window("MyAiAgent", client.base, width=1100, height=720)
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
