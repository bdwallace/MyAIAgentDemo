"""Tool Runtime · 工作区牢。所有文件/Shell/Git 只能动 sandbox/ 里的路径。"""

from __future__ import annotations

from pathlib import Path

from config import settings


def sandbox_root() -> Path:
    root = settings.sandbox_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_sandbox(rel: str | None) -> Path:
    """把相对路径解析到 sandbox 内；试图跳出则报错。"""
    root = sandbox_root()
    raw = (rel or ".").strip() or "."
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("路径必须在 sandbox/ 内") from exc
    return target
