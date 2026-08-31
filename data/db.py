"""Data Layer · PostgreSQL。

V0：conversations / messages。
V0.5：memories。
V0.6：documents / doc_chunks，向量列是 pgvector 的 vector（Docker 里开扩展）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, event, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config import settings


def _engine_url() -> URL:
    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.pg_user,
        password=settings.pg_password,
        host=settings.pg_host,
        port=settings.pg_port,
        database=settings.pg_database,
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


engine = create_engine(_engine_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _register_pgvector(dbapi_connection, _record) -> None:
    from pgvector.psycopg import register_vector

    register_vector(dbapi_connection)


def init_db() -> None:
    from data import memory as _memory  # noqa: F401  注册 memories 表
    from data import rag as _rag  # noqa: F401  注册 documents / doc_chunks

    if not _rag.pgvector_available():
        raise RuntimeError(
            "PostgreSQL 没有 vector 扩展。先在项目根目录执行: docker compose up -d"
        )
    Base.metadata.create_all(engine)
    try:
        _rag.seed_knowledge_if_empty()
    except Exception as exc:
        # 第一次会下载 bge 权重；失败不阻断 Gateway，可稍后在页面入库
        print(f"知识库种子未写入：{exc}")


def ping() -> bool:
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return True


def _as_dict(row: Conversation) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def ensure_conversation(conversation_id: str, title: str = "新对话") -> None:
    with SessionLocal() as session:
        row = session.get(Conversation, conversation_id)
        now = utcnow()
        if row is None:
            session.add(Conversation(id=conversation_id, title=title, created_at=now, updated_at=now))
        else:
            row.updated_at = now
        session.commit()


def list_conversations() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(select(Conversation).order_by(Conversation.updated_at.desc())).all()
        return [_as_dict(r) for r in rows]


def delete_conversation(conversation_id: str) -> bool:
    with SessionLocal() as session:
        row = session.get(Conversation, conversation_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def add_message(conversation_id: str, role: str, content: str, *, create: bool = True) -> bool:
    if create:
        ensure_conversation(conversation_id)
    with SessionLocal() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None:
            return False
        session.add(Message(conversation_id=conversation_id, role=role, content=content))
        conv.updated_at = utcnow()
        if role == "user" and conv.title == "新对话":
            conv.title = content.strip().replace("\n", " ")[:24] or "新对话"
        session.commit()
        return True


def load_messages(conversation_id: str, limit: int) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        ).all()
        return [
            {"role": r.role, "content": r.content}
            for r in reversed(rows)
        ]
