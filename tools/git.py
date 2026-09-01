"""Tool Runtime · 在 sandbox 里操作 Git。仓库不存在时先 git_init。"""

from __future__ import annotations

import os
import shutil
import subprocess

from langchain_core.tools import tool

from config import settings
from tools.sandbox import sandbox_root


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "MyAiAgent")
    env.setdefault("GIT_AUTHOR_EMAIL", "agent@localhost")
    env.setdefault("GIT_COMMITTER_NAME", "MyAiAgent")
    env.setdefault("GIT_COMMITTER_EMAIL", "agent@localhost")
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run_git(*args: str) -> str:
    git = shutil.which("git")
    if not git:
        return "本机没有 git 命令，请先安装 Git for Windows。"
    try:
        completed = subprocess.run(
            [git, *args],
            cwd=str(sandbox_root()),
            capture_output=True,
            text=True,
            timeout=settings.shell_timeout_seconds,
            encoding="utf-8",
            errors="replace",
            env=_git_env(),
        )
    except subprocess.TimeoutExpired:
        return f"git 超时（>{settings.shell_timeout_seconds}s）"
    parts = []
    if completed.stdout.strip():
        parts.append(completed.stdout.strip())
    if completed.stderr.strip():
        parts.append(completed.stderr.strip())
    body = "\n".join(parts) or "（无输出）"
    if completed.returncode != 0:
        return f"git {' '.join(args)} 失败（exit {completed.returncode}）\n{body}"[:8000]
    return body[:8000]


@tool
def git_init() -> str:
    """在 sandbox/ 初始化 git 仓库。已经是仓库则直接说明。"""
    git_dir = sandbox_root() / ".git"
    if git_dir.exists():
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
    added = _run_git("add", "-A")
    if added.startswith("本机没有 git") or "失败" in added:
        return added
    return _run_git("commit", "-m", message)
