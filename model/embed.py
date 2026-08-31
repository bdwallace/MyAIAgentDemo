"""Model Layer · 文本向量。

聊天走 LLM；检索走另一套 embedding。DeepSeek 没有官方 embeddings，
V0.6 默认用本机 bge-small-zh（modelscope 下载）。若配置了
EMBEDDING_BASE_URL，则改走 OpenAI 兼容的 /v1/embeddings。
"""

from __future__ import annotations

from functools import lru_cache

import httpx
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from config import settings

# bge-small-zh-v1.5 查询侧建议加的指令前缀
_QUERY_PREFIX = "为这个句子生成表示以用于检索："


def _http_base() -> str:
    url = (settings.embedding_base_url or "").rstrip("/")
    if url and not url.endswith("/v1"):
        url += "/v1"
    return url


def embedding_backend() -> str:
    if _http_base():
        return "openai-compat"
    return "local-bge"


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    if not texts:
        return []
    payloads = [(_QUERY_PREFIX + t if is_query else t) for t in texts]
    if _http_base():
        return _embed_http(payloads)
    return _embed_local(payloads)


def embed_query(text: str) -> list[float]:
    rows = embed_texts([text], is_query=True)
    return rows[0] if rows else []


@lru_cache(maxsize=1)
def _local_pair():
    from modelscope import snapshot_download

    path = snapshot_download(settings.embedding_model)
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModel.from_pretrained(path)
    model.eval()
    return tokenizer, model


def _mean_pool(last_hidden: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    mask = mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = (last_hidden * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    return F.normalize(summed / counts, p=2, dim=1)


def _embed_local(texts: list[str]) -> list[list[float]]:
    tokenizer, model = _local_pair()
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    with torch.no_grad():
        hidden = model(**encoded).last_hidden_state
        vecs = _mean_pool(hidden, encoded["attention_mask"])
    return vecs.cpu().tolist()


def _embed_http(texts: list[str]) -> list[list[float]]:
    key = (settings.embedding_api_key or settings.llm_api_key or "local").strip()
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{_http_base()}/embeddings",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": settings.embedding_model, "input": texts},
        )
        response.raise_for_status()
        payload = response.json()
    rows = sorted(payload.get("data") or [], key=lambda item: item.get("index", 0))
    return [item["embedding"] for item in rows]