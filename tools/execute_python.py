"""在 sandbox/ 里跑 Python。V0 用子进程+超时，不是安全沙箱。"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

from langchain_core.tools import tool

from config import settings


@tool
def execute_python(code: str) -> str:
    """执行 Python 代码并返回 stdout/stderr。计算、写小脚本时使用。需要看到结果请 print。"""
    sandbox: Path = settings.sandbox_dir
    sandbox.mkdir(parents=True, exist_ok=True)
    script = sandbox / f"run_{uuid.uuid4().hex}.py"
    script.write_text(code, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(sandbox),
            capture_output=True,
            text=True,
            timeout=settings.python_timeout_seconds,
            encoding="utf-8",
            errors="replace",
        )
        parts = []
        if completed.stdout.strip():
            parts.append(completed.stdout.strip())
        if completed.stderr.strip():
            parts.append("[stderr]\n" + completed.stderr.strip())
        return ("\n".join(parts) or "（无输出，请 print 结果）")[:8000]
    except subprocess.TimeoutExpired:
        return f"执行超时（>{settings.python_timeout_seconds}s）"
    finally:
        script.unlink(missing_ok=True)
