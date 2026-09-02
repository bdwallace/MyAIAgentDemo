"""启动时建表、ping Redis、预热 embedding。manage.py check 不会走到这里。"""

from __future__ import annotations

_booted = False


def ensure_ready() -> None:
    global _booted
    if _booted:
        return
    from data.cache import ping as redis_ping
    from data.db import init_db, ping

    try:
        init_db()
        ping()
        if not redis_ping():
            raise RuntimeError("Redis 连不上")
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL 或 Redis 连不上。先在项目根目录执行: docker compose up -d"
            "（Postgres 5433，Redis 6379）"
        ) from exc
    _booted = True
