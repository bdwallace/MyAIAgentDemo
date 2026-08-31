"""Agent Runtime · Memory。

职责：决定「这一轮 LLM 能看见哪些长期记忆」。
落库、增删改查在 Data Layer（data/memory.py）；这里只做装配。
"""

from config import settings
from data.memory import list_memories


def prompt_block() -> str:
    """给 reason 用的文本块。读库在 Data Layer；这里只决定塞进 Prompt 的条数和格式。"""
    rows = list_memories(limit=settings.max_memories_in_prompt)
    if not rows:
        return "（还没有长期记忆）"
    lines = [f"- [{row['kind']}] {row['key']}：{row['content']}" for row in rows]
    return "\n".join(lines)
