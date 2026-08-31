"""Data Layer · RAG 文档块。

不把私有文档塞进 memories：那是用户事实，这是可检索资料。
向量列是 pgvector 的 vector，检索用 <=>（余弦距离）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import ROOT_DIR, settings
from data.db import Base, SessionLocal, utcnow

KNOWLEDGE_DIR = ROOT_DIR / "docs" / "knowledge"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "doc_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    document: Mapped[Document] = relationship(back_populates="chunks")


_pgvector_ok: bool | None = None


def pgvector_available() -> bool:
    global _pgvector_ok
    if _pgvector_ok is not None:
        return _pgvector_ok
    from data.db import engine

    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        _pgvector_ok = True
    except Exception:
        _pgvector_ok = False
    return _pgvector_ok


def _as_doc(row: Document, chunk_n: int) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "source": row.source,
        "chunk_count": chunk_n,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def split_text(text_body: str) -> list[str]:
    size = settings.rag_chunk_size
    overlap = settings.rag_chunk_overlap
    raw = (text_body or "").replace("\r\n", "\n").strip()
    if not raw:
        return []
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    pieces: list[str] = []
    for para in paragraphs or [raw]:
        if len(para) <= size:
            pieces.append(para)
            continue
        i = 0
        while i < len(para):
            pieces.append(para[i : i + size])
            i += max(size - overlap, 1)
    return pieces


def ingest_document(title: str, content: str, source: str = "") -> dict[str, Any]:
    title = (title or "").strip()[:200] or "未命名文档"
    chunks = split_text(content)
    if not chunks:
        raise ValueError("正文是空的")
    from model.embed import embed_texts

    vectors = embed_texts(chunks, is_query=False)
    with SessionLocal() as session:
        doc = Document(title=title, source=source.strip())
        session.add(doc)
        session.flush()
        for i, (piece, vec) in enumerate(zip(chunks, vectors)):
            session.add(Chunk(document_id=doc.id, ordinal=i, content=piece, embedding=vec))
        session.commit()
        return _as_doc(doc, chunk_n=len(chunks))


def list_documents() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(select(Document).order_by(Document.id.desc())).all()
        out = []
        for row in rows:
            n = session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == row.id)
            )
            out.append(_as_doc(row, chunk_n=int(n or 0)))
        return out


def delete_document(document_id: int) -> bool:
    with SessionLocal() as session:
        row = session.get(Document, document_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def chunk_count() -> int:
    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(Chunk)) or 0)


def search_chunks(query: str, limit: int | None = None) -> list[dict[str, Any]]:
    """问题编成向量，用 pgvector <=> 按余弦距离取 top-k。"""
    query = (query or "").strip()
    if not query:
        return []
    k = limit or settings.rag_top_k
    from model.embed import embed_query

    qvec = embed_query(query)
    dist = Chunk.embedding.cosine_distance(qvec)
    with SessionLocal() as session:
        rows = session.execute(
            select(Chunk, dist.label("dist")).order_by(dist).limit(k)
        ).all()
        out = []
        for row, distance in rows:
            score = 1.0 - float(distance)
            if score < settings.rag_min_score:
                continue
            doc = session.get(Document, row.document_id)
            out.append(
                {
                    "chunk_id": row.id,
                    "document_id": row.document_id,
                    "title": doc.title if doc else "",
                    "content": row.content,
                    "score": round(score, 4),
                }
            )
        return out


def seed_knowledge_if_empty() -> None:
    """第一次启动时，把 docs/knowledge 下的 md/txt 灌进库，方便验证 RAG。"""
    if chunk_count() > 0 or not KNOWLEDGE_DIR.is_dir():
        return
    for path in sorted(KNOWLEDGE_DIR.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        ingest_document(title=path.stem, content=path.read_text(encoding="utf-8"), source=str(path))
