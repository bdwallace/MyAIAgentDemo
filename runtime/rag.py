"""Agent Runtime · RAG。

职责：根据当前用户问题取出最相关的文档块，交给 reason 塞进 Prompt。
切块、向量、落库在 Data Layer；这里只装配。
"""

from data.rag import search_chunks


def prompt_block(question: str) -> str:
    hits = search_chunks(question)
    if not hits:
        return "（知识库没有足够相似的片段）"
    lines = []
    for i, hit in enumerate(hits, 1):
        lines.append(
            f"[{i}] 《{hit['title']}》(相似度 {hit['score']})\n{hit['content']}"
        )
    return "\n\n".join(lines)
