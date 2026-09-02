"""Data Layer · Redis。

V1.5：两件事共用一个 Redis。
  1. 短 TTL 缓存（RAG 检索）
  2. Celery 的 broker / result backend
聊天状态仍在 PostgreSQL，不要把会话搬进 Redis。
"""

from __future__ import annotations

import json
from typing import Any

import redis

from config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def ping() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def rag_epoch() -> int:
    try:
        return int(get_redis().get("rag:epoch") or 0)
    except Exception:
        return 0


def bump_rag_cache() -> None:
    try:
        get_redis().incr("rag:epoch")
    except Exception:
        pass


def cache_get(key: str) -> Any | None:
    try:
        raw = get_redis().get(key)
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        get_redis().setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception:
        pass
