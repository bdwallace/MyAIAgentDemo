"""在隔离容器里跑 Python。用的是容器解释器，看不到宿主机 .venv / .env。"""

from __future__ import annotations

import uuid

from langchain_core.tools import tool

from config import settings
from tools.sandbox import run_in_jail, sandbox_root


@tool
def execute_python(code: str) -> str:
    """在安全沙箱里执行 Python 并返回 stdout/stderr。需要看到结果请 print。工作目录是 sandbox/。"""
    code = code or ""
    if len(code.encode("utf-8")) > settings.sandbox_write_max_bytes:
        return f"代码超过 {settings.sandbox_write_max_bytes} 字节，拒绝执行。"
    sandbox = sandbox_root()
    name = f"run_{uuid.uuid4().hex}.py"
    script = sandbox / name
    script.write_text(code, encoding="utf-8")
    try:
        return run_in_jail(
            ["python", f"/workspace/{name}"],
            timeout=settings.python_timeout_seconds,
        )
    finally:
        script.unlink(missing_ok=True)
