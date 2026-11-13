"""Redis 缓存与限流，缺少 Redis 时回退到 fakeredis。"""
from __future__ import annotations

import time

from .config import REDIS_URL

_client = None


def get_redis():
    global _client
    if _client is not None:
        return _client
    if REDIS_URL:
        import redis

        _client = redis.from_url(REDIS_URL, decode_responses=True)
    else:
        try:
            import fakeredis

            _client = fakeredis.FakeStrictRedis(decode_responses=True)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("未配置 REDIS_URL，且未安装 fakeredis，无法使用缓存") from exc
    return _client


def cache_get(key: str):
    return get_redis().get(key)


def cache_set(key: str, value: str, ttl_seconds: int | None = None) -> None:
    client = get_redis()
    if ttl_seconds:
        client.set(key, value, ex=ttl_seconds)
    else:
        client.set(key, value)


def rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """返回 True 表示未超限，False 表示超限。"""
    client = get_redis()
    current = client.get(key)
    if current is None:
        pipe = client.pipeline()
        pipe.set(key, 1, ex=window_seconds)
        pipe.execute()
        return True
    count = int(current)
    if count >= limit:
        return False
    pipe = client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    pipe.execute()
    return True
