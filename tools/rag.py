"""Tool Runtime · 私有知识库。检索走向量，不是网页搜索。"""

from langchain_core.tools import tool

from data.rag import ingest_document, search_chunks


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
    """把一段文本切块、向量化后写入知识库。用户明确说「记到知识库/入库」时使用。"""
    try:
        row = ingest_document(title=title, content=content, source="tool")
    except ValueError as exc:
        return f"入库失败：{exc}"
    return f"已入库《{row['title']}》，切成 {row['chunk_count']} 块。"
