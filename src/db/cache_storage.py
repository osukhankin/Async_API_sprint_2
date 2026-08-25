from abc import ABC, abstractmethod


class CacheStorage(ABC):
    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Значение по ключу или None, если его нет или кеш недоступен."""

    @abstractmethod
    async def set(
        self,
        key: str,
        value: str | bytes,
        expire: int | None = None,
    ) -> None:
        """Сохранить значение. Ошибка кеша не должна пробрасываться наружу."""
