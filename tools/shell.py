"""Tool Runtime · 在 sandbox 里跑 Shell。有超时和路径限制，不是安全沙箱。"""

from __future__ import annotations

import re
import subprocess

from langchain_core.tools import tool

from config import settings
from tools.sandbox import sandbox_root

_BLOCKED = (
    "shutdown",
    "format ",
    "reg delete",
    "rmdir /s",
    "rd /s",
    "del /f",
    "mkfs",
    "diskpart",
)


def _reject(command: str) -> str | None:
    if ".." in command:
        return "不允许使用 .. 跳出 sandbox。"
    if re.search(r"[a-zA-Z]:[\\/]", command):
        return "不允许绝对路径，命令会在 sandbox/ 下执行。"
    lower = command.lower()
    for token in _BLOCKED:
        if token in lower:
            return f"拒绝执行含 `{token.strip()}` 的命令。"
    return None


@tool
def execute_shell(command: str) -> str:
    """在 sandbox/ 目录执行一条 Shell 命令（Windows 上走 cmd）。看目录、跑 git 以外的小命令时使用。"""
    command = (command or "").strip()
    if not command:
        return "命令是空的。"
    reason = _reject(command)
    if reason:
        return reason
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(sandbox_root()),
            capture_output=True,
            text=True,
            timeout=settings.shell_timeout_seconds,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"执行超时（>{settings.shell_timeout_seconds}s）"
    except Exception as exc:
        return f"执行失败：{exc}"
    parts = []
    if completed.stdout.strip():
        parts.append(completed.stdout.strip())
    if completed.stderr.strip():
        parts.append("[stderr]\n" + completed.stderr.strip())
    code = completed.returncode
    body = "\n".join(parts) or "（无输出）"
    return f"exit {code}\n{body}"[:8000]
