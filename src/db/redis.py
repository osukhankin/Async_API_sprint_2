from logging import getLogger
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.backoff import backoff
from .cache_storage import CacheStorage

logger = getLogger(__name__)

redis: Optional[Redis] = None
cache_storage: Optional[CacheStorage] = None


class RedisCacheStorage(CacheStorage):
    def __init__(self, client: Redis):
        self._client = client

    async def get(self, key: str) -> bytes | None:
        try:
            return await self._get(key)
        except RedisError as exc:
            logger.error('Redis unavailable on get(%s): %s', key, exc)
            return None

    async def set(
        self,
        key: str,
        value: str | bytes,
        expire: int | None = None,
    ) -> None:
        try:
            await self._set(key, value, expire)
        except RedisError as exc:
            logger.error('Redis unavailable on set(%s): %s', key, exc)

    async def delete(self, key: str) -> None:
        try:
            await self._delete(key)
        except RedisError as exc:
            logger.error('Redis unavailable on delete(%s): %s', key, exc)

    @backoff(exceptions=(RedisError,))
    async def _get(self, key: str) -> bytes | None:
        return await self._client.get(key)

    @backoff(exceptions=(RedisError,))
    async def _set(
        self,
        key: str,
        value: str | bytes,
        expire: int | None = None,
    ) -> None:
        await self._client.set(key, value, ex=expire)

    @backoff(exceptions=(RedisError,))
    async def _delete(self, key: str) -> None:
        await self._client.delete(key)


async def get_cache_storage() -> CacheStorage:
    return cache_storage
