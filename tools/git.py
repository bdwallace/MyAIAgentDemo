"""在隔离容器里操作 sandbox 的 Git。不依赖宿主机是否安装 Git。"""

from __future__ import annotations

from langchain_core.tools import tool

from config import settings
from tools.sandbox import run_in_jail, sandbox_root


def _run_git(*args: str) -> str:
    return run_in_jail(
        ["git", *args],
        timeout=settings.shell_timeout_seconds,
        extra_env={
            "GIT_AUTHOR_NAME": "MyAiAgent",
            "GIT_AUTHOR_EMAIL": "agent@localhost",
            "GIT_COMMITTER_NAME": "MyAiAgent",
            "GIT_COMMITTER_EMAIL": "agent@localhost",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


@tool
def git_init() -> str:
    """在 sandbox/ 初始化 git 仓库。已经是仓库则直接说明。"""
    if (sandbox_root() / ".git").exists():
        return "sandbox/ 已经是 git 仓库。"
    return _run_git("init")


@tool
def git_status() -> str:
    """查看 sandbox 仓库的 git status。"""
    return _run_git("status")


@tool
def git_log() -> str:
    """查看最近提交（最多 8 条）。"""
    return _run_git("log", "-8", "--oneline")


@tool
def git_diff() -> str:
    """查看未提交的 diff（含未暂存）。"""
    return _run_git("diff", "HEAD")


@tool
def git_commit(message: str) -> str:
    """把 sandbox 里所有改动 add 后提交。message 是提交说明。"""
    message = (message or "").strip() or "agent commit"
    if "\x00" in message or "\n" in message:
        return "提交说明不能包含换行。"
    added = _run_git("add", "-A")
    if added.startswith("本机没有") or added.startswith("沙箱") or added.startswith("exit "):
        return added
    return _run_git("commit", "-m", message)
