"""A cache-aside wrapper around Redis.

Every method degrades to a no-op (a miss on read, a silent drop on write)
if Redis is unreachable, rather than raising - a cache outage should cost
performance, never correctness or availability. Short connect/socket
timeouts keep a dead Redis from turning into a slow request instead of a
fast fallback.
"""

import logging

import redis

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_SECONDS = 1
_SOCKET_TIMEOUT_SECONDS = 1


class Cache:
    def __init__(self, redis_url: str) -> None:
        self._client: redis.Redis = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=_SOCKET_TIMEOUT_SECONDS,
            decode_responses=True,
        )

    def get(self, key: str) -> str | None:
        try:
            value = self._client.get(key)
            return str(value) if value is not None else None
        except redis.RedisError as exc:
            logger.warning("Cache read failed for key %r: %s", key, exc)
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds)
        except redis.RedisError as exc:
            logger.warning("Cache write failed for key %r: %s", key, exc)
