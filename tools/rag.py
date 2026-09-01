"""Tool Runtime · 私有知识库。入库走 Celery，检索可走 Redis 缓存。"""

import time

from langchain_core.tools import tool

from data.rag import search_chunks


@tool
def search_docs(query: str) -> str:
    """在私有知识库里按语义检索。问内部手册、已入库文档时用，不要用 search_web 代替。"""
    hits = search_chunks(query)
    if not hits:
        return "知识库里没有足够相似的内容。可以先入库，或换个问法。"
    lines = []
    for hit in hits:
        lines.append(f"《{hit['title']}》 score={hit['score']}\n{hit['content']}")
    return "\n\n".join(lines)


@tool
def ingest_doc(title: str, content: str) -> str:
    """把一段文本切块、向量化后写入知识库。真正的向量化在 Celery worker 里跑。"""
    from worker.jobs import enqueue_ingest, job_status

    try:
        queued = enqueue_ingest(title=title, content=content, source="tool")
    except Exception as exc:
        return f"排队失败：{exc}"
    job_id = queued["job_id"]
    for _ in range(90):
        info = job_status(job_id)
        if info["status"] == "SUCCESS":
            row = info["result"] or {}
            return f"已入库《{row.get('title')}》，切成 {row.get('chunk_count')} 块。"
        if info["status"] == "FAILURE":
            return f"入库失败：{info['error']}"
        time.sleep(1)
    return f"入库仍在排队（job_id={job_id}）。请另开终端运行 .\\scripts\\run_worker.ps1"
