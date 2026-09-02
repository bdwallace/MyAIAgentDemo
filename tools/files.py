"""Tool Runtime · 沙箱文件系统。在 Gateway 进程里读写，但仍受路径牢约束。"""

from langchain_core.tools import tool

from config import settings
from tools.sandbox import resolve_in_sandbox, sandbox_root


@tool
def list_dir(path: str = ".") -> str:
    """列出 sandbox 里某个目录的文件和子目录。path 相对 sandbox/，默认当前目录。"""
    try:
        folder = resolve_in_sandbox(path)
    except ValueError as exc:
        return str(exc)
    if not folder.exists():
        return f"不存在：{path}"
    if not folder.is_dir():
        return f"不是目录：{path}"
    root = sandbox_root()
    lines = []
    for child in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = child.relative_to(root).as_posix()
        mark = "dir " if child.is_dir() else "file"
        size = "" if child.is_dir() else f" {child.stat().st_size}B"
        lines.append(f"{mark} {rel}{size}")
    return "\n".join(lines) or "（空目录）"


@tool
def read_file(path: str) -> str:
    """读取 sandbox 内的文本文件。"""
    try:
        target = resolve_in_sandbox(path)
    except ValueError as exc:
        return str(exc)
    if not target.is_file():
        return f"不是文件或不存在：{path}"
    if target.stat().st_size > 200_000:
        return "文件超过 200KB，拒绝读取。"
    return target.read_text(encoding="utf-8", errors="replace")[:8000]


@tool
def write_file(path: str, content: str) -> str:
    """写入 sandbox 内的文本文件。目录不存在时会创建。覆盖已有文件。"""
    try:
        target = resolve_in_sandbox(path)
    except ValueError as exc:
        return str(exc)
    if target.exists() and target.is_dir():
        return f"是目录，不能当文件写：{path}"
    payload = content or ""
    if len(payload.encode("utf-8")) > settings.sandbox_write_max_bytes:
        return f"内容超过 {settings.sandbox_write_max_bytes} 字节，拒绝写入。"
    if target == sandbox_root():
        return "不能覆盖 sandbox 根目录。"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    rel = target.relative_to(sandbox_root()).as_posix()
    return f"已写入 {rel}（{target.stat().st_size} 字节）"


@tool
def delete_file(path: str) -> str:
    """删除 sandbox 内的一个文件（不能删目录）。"""
    try:
        target = resolve_in_sandbox(path)
    except ValueError as exc:
        return str(exc)
    if not target.is_file():
        return f"不是文件或不存在：{path}"
    rel = target.relative_to(sandbox_root()).as_posix()
    target.unlink()
    return f"已删除 {rel}"
