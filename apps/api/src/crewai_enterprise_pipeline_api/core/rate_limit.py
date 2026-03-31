from __future__ import annotations

import asyncio
import time
from functools import lru_cache

from redis.asyncio import Redis

from crewai_enterprise_pipeline_api.core.settings import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis: Redis | None = None
        self._memory_windows: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.settings.redis_url, encoding="utf-8", decode_responses=True)
        return self._redis

    async def hit(self, key: str, *, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        if not self.settings.rate_limit_enabled:
            return True, limit

        try:
            redis = self._get_redis()
            current_value = await redis.incr(key)
            if current_value == 1:
                await redis.expire(key, window_seconds)
            remaining = max(limit - int(current_value), 0)
            return current_value <= limit, remaining
        except Exception:
            return await self._memory_hit(key, limit=limit, window_seconds=window_seconds)

    async def _memory_hit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        async with self._lock:
            now = time.time()
            reset_at, count = self._memory_windows.get(key, (now + window_seconds, 0))
            if reset_at <= now:
                reset_at, count = now + window_seconds, 0
            count += 1
            self._memory_windows[key] = (reset_at, count)
            remaining = max(limit - count, 0)
            return count <= limit, remaining

    async def close(self) -> None:
        self._memory_windows.clear()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter()
