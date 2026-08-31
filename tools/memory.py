"""Tool Runtime · 长期记忆。写/查/删都走 Data Layer，不经过向量库。"""

from langchain_core.tools import tool

from data.memory import delete_memory_by_key, search_memories, upsert_memory


@tool
def remember(key: str, content: str, kind: str = "fact") -> str:
    """把跨对话仍有用的事实写入长期记忆。key 是短标签（如 姓名、城市），同类 key 会覆盖。
    kind 只能是 profile / preference / fact / note。一次性问题不要记。"""
    try:
        row = upsert_memory(key=key, content=content, kind=kind)
    except ValueError as exc:
        return f"写入失败：{exc}"
    return f"已记住 [{row['kind']}] {row['key']}：{row['content']}"


@tool
def recall(query: str) -> str:
    """按关键字检索长期记忆。系统提示里已经有一份摘要；这里用于精确查找或确认是否记过。"""
    rows = search_memories(query, limit=8)
    if not rows:
        return "没有找到匹配的长期记忆。" if query.strip() else "长期记忆是空的。"
    lines = [f"- [{row['kind']}] {row['key']}：{row['content']}" for row in rows]
    return "\n".join(lines)


@tool
def forget(key: str) -> str:
    """按 key 删除一条长期记忆。用户说忘掉、不要再提某事时使用。"""
    if delete_memory_by_key(key):
        return f"已忘记：{key}"
    return f"没有叫「{key}」的记忆。"
