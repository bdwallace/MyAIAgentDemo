from langchain_core.tools import tool

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


@tool
def search_web(query: str) -> str:
    """搜索互联网，返回标题、链接和摘要。查新闻、文档、公开事实时使用。"""
    try:
        with DDGS() as client:
            results = list(client.text(query, max_results=5))
    except Exception as exc:
        return f"搜索失败：{exc}"
    if not results:
        return "没有搜到结果。"
    lines = []
    for i, item in enumerate(results, 1):
        title = item.get("title") or ""
        href = item.get("href") or item.get("url") or ""
        body = item.get("body") or item.get("snippet") or ""
        lines.append(f"{i}. {title}\n   {href}\n   {body}")
    return "\n".join(lines)
