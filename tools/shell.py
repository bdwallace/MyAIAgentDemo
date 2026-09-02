"""在隔离容器里跑 Shell（Linux sh）。能出网，不能碰到宿主机文件系统。"""

from __future__ import annotations

from langchain_core.tools import tool

from config import settings
from tools.sandbox import run_in_jail


@tool
def execute_shell(command: str) -> str:
    """在安全沙箱里用 sh -lc 执行一条命令。用 ls/cat，不要用 Windows 的 dir。工作目录是 sandbox/。"""
    command = (command or "").strip()
    if not command:
        return "命令是空的。"
    if len(command) > 4000:
        return "命令太长，拒绝执行。"
    result = run_in_jail(
        ["sh", "-lc", command],
        timeout=settings.shell_timeout_seconds,
    )
    if result.startswith("exit ") or result.startswith("执行超时") or result.startswith("本机没有") or result.startswith("沙箱"):
        return result
    return f"exit 0\n{result}"
