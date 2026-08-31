"""Data Layer · 长期记忆表。

V0 的 conversations/messages 是短时记忆（当前对话窗口）。
V0.5 的 memories 跨对话存活。检索先用关键字；V0.6 再上 pgvector。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column

from data.db import Base, SessionLocal, utcnow

KINDS = ("profile", "preference", "fact", "note")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), default="fact")
    key: Mapped[str] = mapped_column(String(80), unique=True)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _as_dict(row: Memory) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "key": row.key,
        "content": row.content,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _clean_key(key: str) -> str:
    return " ".join((key or "").strip().split())[:80]


def upsert_memory(key: str, content: str, kind: str = "fact") -> dict[str, Any]:
    key = _clean_key(key)
    content = (content or "").strip()
    kind = (kind or "fact").strip().lower()
    if kind not in KINDS:
        kind = "fact"
    if not key:
        raise ValueError("记忆 key 不能为空")
    if not content:
        raise ValueError("记忆内容不能为空")

    with SessionLocal() as session:
        row = session.scalar(select(Memory).where(Memory.key == key))
        now = utcnow()
        if row is None:
            row = Memory(kind=kind, key=key, content=content, created_at=now, updated_at=now)
            session.add(row)
        else:
            row.kind = kind
            row.content = content
            row.updated_at = now
        session.commit()
        session.refresh(row)
        return _as_dict(row)


def list_memories(limit: int = 100) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Memory).order_by(Memory.updated_at.desc()).limit(limit)
        ).all()
        return [_as_dict(r) for r in rows]


def search_memories(query: str, limit: int = 8) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return list_memories(limit=limit)
    pattern = f"%{query}%"
    with SessionLocal() as session:
        rows = session.scalars(
            select(Memory)
            .where(or_(Memory.key.ilike(pattern), Memory.content.ilike(pattern)))
            .order_by(Memory.updated_at.desc())
            .limit(limit)
        ).all()
        return [_as_dict(r) for r in rows]


def delete_memory(memory_id: int) -> bool:
    with SessionLocal() as session:
        row = session.get(Memory, memory_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def delete_memory_by_key(key: str) -> bool:
    key = _clean_key(key)
    with SessionLocal() as session:
        row = session.scalar(select(Memory).where(Memory.key == key))
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def memory_count() -> int:
    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(Memory)) or 0)
