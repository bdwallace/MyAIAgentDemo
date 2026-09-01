from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from config import settings


@tool
def browse_page(url: str) -> str:
    """打开一个 http/https 页面，返回去标签后的正文。search_web 拿到链接后，需要细节时再用。"""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "只允许 http/https 链接。"
    try:
        with httpx.Client(
            timeout=settings.web_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "MyAiAgent/v1"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        return f"打开页面失败：{exc}"

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "iframe"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = " ".join(soup.get_text("\n").split())[:6000]
    return f"标题: {title}\nURL: {url}\n\n{text}"
