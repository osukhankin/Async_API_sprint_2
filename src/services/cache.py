from functools import lru_cache
from logging import getLogger
from typing import TypeVar

from fastapi import Depends
from pydantic import BaseModel, TypeAdapter, ValidationError

from core.config import settings
from db.cache_storage import CacheStorage
from db.redis import get_cache_storage

T = TypeVar('T')
ModelT = TypeVar('ModelT', bound=BaseModel)

logger = getLogger(__name__)


class CacheService:
    def __init__(self, storage: CacheStorage):
        self._storage = storage

    async def get(self, key: str) -> bytes | None:
        return await self._storage.get(key)

    async def set(self, key: str, value: str | bytes) -> None:
        await self._storage.set(key, value, expire=settings.cache_expire_in_seconds)

    async def delete(self, key: str) -> None:
        await self._storage.delete(key)

    async def get_model(self, key: str, model: type[ModelT]) -> ModelT | None:
        data = await self.get(key)
        if not data:
            return None
        try:
            return model.model_validate_json(data)
        except ValidationError as exc:
            await self._drop_invalid_cache(
                key=key,
                schema=model.__name__,
                data=data,
                exc=exc,
            )
            return None

    async def set_model(self, key: str, value: BaseModel) -> None:
        await self.set(key, value.model_dump_json())

    async def get_typed(self, key: str, adapter: TypeAdapter[T]) -> T | None:
        data = await self.get(key)
        if not data:
            return None
        try:
            return adapter.validate_json(data)
        except ValidationError as exc:
            await self._drop_invalid_cache(
                key=key,
                schema=str(adapter),
                data=data,
                exc=exc,
            )
            return None

    async def set_typed(self, key: str, adapter: TypeAdapter[T], value: T) -> None:
        await self.set(key, adapter.dump_json(value))

    async def _drop_invalid_cache(
        self,
        key: str,
        schema: str,
        data: bytes,
        exc: ValidationError,
    ) -> None:
        preview = data[:200]
        logger.warning(
            'Invalid cache value key=%s schema=%s value_preview=%r error=%s. Dropping key.',
            key,
            schema,
            preview,
            exc,
            exc_info=True,
        )
        await self.delete(key)


@lru_cache()
def get_cache_service(
    storage: CacheStorage = Depends(get_cache_storage),
) -> CacheService:
    return CacheService(storage)
