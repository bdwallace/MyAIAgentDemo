"""Tool Runtime · 安全沙箱。

两层：
  1. 路径牢：文件工具只能碰 sandbox/（跟符号链接 / 绝对路径）。
  2. 进程牢：Python / Shell / Git 在 Docker 容器里跑。
     能出网，但不进 compose 内网；只读根文件系统、丢光 capability、内存/进程数封顶。
     不把宿主机环境变量和 Docker socket 传进去。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from config import ROOT_DIR, settings

_ABS_WIN = re.compile(r"^[a-zA-Z]:[\\/]")


def sandbox_root() -> Path:
    root = settings.sandbox_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_sandbox(rel: str | None) -> Path:
    """把相对路径解析到 sandbox 内；绝对路径、UNC、跳出目录一律拒绝。"""
    raw = (rel or ".").replace("\x00", "").strip() or "."
    if raw.startswith(("\\\\", "//")) or _ABS_WIN.match(raw) or raw.startswith("/"):
        raise ValueError("路径必须相对 sandbox/，不允许绝对路径。")
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError("路径必须相对 sandbox/，不允许绝对路径。")
    root = sandbox_root()
    target = (root / candidate).resolve()
    if not target.is_relative_to(root):
        raise ValueError("路径必须在 sandbox/ 内")
    return target


def _docker(*args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def jail_running() -> bool:
    try:
        result = _docker(
            "inspect",
            "-f",
            "{{.State.Running}}",
            settings.sandbox_container,
            timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def jail_status() -> dict:
    return {
        "ok": jail_running(),
        "backend": "docker",
        "container": settings.sandbox_container,
    }


def ensure_jail() -> str | None:
    """容器没起来就尝试 start / compose up。成功返回 None。"""
    if jail_running():
        return None
    try:
        _docker("start", settings.sandbox_container, timeout=30)
        if jail_running():
            return None
    except FileNotFoundError:
        return "本机没有 docker。安全沙箱需要 Docker Desktop。"
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"无法启动沙箱容器：{exc}"
    try:
        built = subprocess.run(
            ["docker", "compose", "up", "-d", "--build", "sandbox"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return "本机没有 docker。安全沙箱需要 Docker Desktop。"
    except subprocess.TimeoutExpired:
        return "构建/启动沙箱超时。请手动执行: docker compose up -d --build sandbox"
    if built.returncode != 0 or not jail_running():
        detail = (built.stderr or built.stdout or "").strip()[:500]
        return "沙箱容器没起来。请执行: docker compose up -d --build sandbox" + (
            f"\n{detail}" if detail else ""
        )
    return None


def _kill_stray() -> None:
    try:
        _docker(
            "exec",
            "-u",
            settings.sandbox_exec_user,
            settings.sandbox_container,
            "sh",
            "-c",
            "killall -q -9 python git timeout 2>/dev/null || true",
            timeout=8,
        )
    except Exception:
        pass


def run_in_jail(
    argv: list[str],
    timeout: int,
    extra_env: dict[str, str] | None = None,
) -> str:
    """在隔离容器里执行 argv（不要走宿主机 shell）。"""
    if not argv:
        return "命令是空的。"
    err = ensure_jail()
    if err:
        return err
    cmd = [
        "docker",
        "exec",
        "-w",
        "/workspace",
        "-u",
        settings.sandbox_exec_user,
        "-e",
        "HOME=/tmp",
        "-e",
        "GIT_TERMINAL_PROMPT=0",
        "-e",
        "GIT_CONFIG_NOSYSTEM=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
    ]
    for key, value in (extra_env or {}).items():
        if key and value is not None:
            cmd.extend(["-e", f"{key}={value}"])
    cmd.extend(
        [
            settings.sandbox_container,
            "timeout",
            "-s",
            "KILL",
            str(max(1, int(timeout))),
            *argv,
        ]
    )
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        _kill_stray()
        return f"执行超时（>{timeout}s），已中止容器内进程。"
    except FileNotFoundError:
        return "本机没有 docker。安全沙箱需要 Docker Desktop。"
    except Exception as exc:
        return f"沙箱执行失败：{exc}"
    parts = []
    if completed.stdout.strip():
        parts.append(completed.stdout.strip())
    if completed.stderr.strip():
        parts.append("[stderr]\n" + completed.stderr.strip())
    body = "\n".join(parts) or "（无输出）"
    if completed.returncode != 0:
        return f"exit {completed.returncode}\n{body}"[:8000]
    return body[:8000]
