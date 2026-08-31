"""Model Layer · OpenAI 兼容协议。

云端：DeepSeek / OpenAI
本地：Ollama / LM Studio / llama.cpp / vLLM
只要对方提供 /v1/chat/completions，这里不用改业务代码。
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from langchain_openai import ChatOpenAI

from config import settings


def openai_base_url() -> str:
    url = settings.llm_base_url.rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    return url


def is_local_llm() -> bool:
    host = (urlparse(openai_base_url()).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def llm_api_key() -> str:
    # 本地服务通常不校验 Key，但 OpenAI SDK 要求字符串非空
    if settings.llm_api_key.strip() and settings.llm_api_key.strip() != "sk-your-key":
        return settings.llm_api_key.strip()
    if is_local_llm():
        return "local"
    return ""


def llm_configured() -> bool:
    if is_local_llm():
        return True
    return bool(llm_api_key())


def build_llm() -> ChatOpenAI:
    """组装 ChatOpenAI。换云端/本地只改 .env 的 BASE_URL / KEY / MODEL。"""
    key = llm_api_key()
    if not key:
        raise RuntimeError("云端模型需要 LLM_API_KEY；本地模型把 LLM_BASE_URL 设成 http://127.0.0.1:端口/v1 即可")
    kwargs: dict = {
        "model": settings.llm_model,
        "api_key": key,
        "base_url": openai_base_url(),
        "temperature": 0.3,
        "streaming": True,
        "timeout": settings.llm_timeout_seconds,
        "max_tokens": 512,
    }
    if is_local_llm():
        # CPU/磁盘卸载时 token 间隔经常超过 120s，默认会误判断线
        kwargs["stream_chunk_timeout"] = None
    return ChatOpenAI(**kwargs)


def inspect_llm() -> dict:
    """探测兼容接口是否活着，本地时可列出已加载模型。"""
    info = {
        "local": is_local_llm(),
        "base_url": openai_base_url(),
        "model": settings.llm_model,
        "ready": False,
        "models": [],
        "error": "",
    }
    if not is_local_llm() and not llm_api_key():
        info["error"] = "未配置 LLM_API_KEY"
        return info

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{openai_base_url()}/models",
                headers={"Authorization": f"Bearer {llm_api_key() or 'local'}"},
            )
    except Exception as exc:
        info["error"] = (
            f"连不上模型服务：{exc}。请确认 transformers serve / Ollama / LM Studio 已启动。"
        )
        return info

    if response.status_code >= 500:
        # transformers serve 在缓存目录为空时 /v1/models 会 500，但 chat 接口仍可用
        info["ready"] = True
        info["error"] = "模型服务已启动；首次对话会下载权重，可能要等几分钟。"
        return info

    try:
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        info["error"] = f"模型服务响应异常：{exc}"
        return info

    models = []
    for item in payload.get("data") or []:
        name = item.get("id")
        if name:
            models.append(name)
    info["models"] = models
    info["ready"] = True
    from pathlib import Path
    local_dir = Path(settings.llm_model)
    if local_dir.is_dir():
        return info
    if models and settings.llm_model not in models:
        info["error"] = (
            f"服务已启动，但没有模型 `{settings.llm_model}`。可用：{', '.join(models[:8])}"
        )
        info["ready"] = False
    return info
