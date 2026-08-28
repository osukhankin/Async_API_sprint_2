from abc import ABC, abstractmethod
from typing import Any


class SearchEngine(ABC):
    @abstractmethod
    async def get(self, index: str, doc_id: str) -> dict[str, Any] | None:
        """Документ по id или None, если его нет."""

    @abstractmethod
    async def search(
        self,
        index: str,
        query: dict[str, Any],
        *,
        from_: int = 0,
        size: int = 10,
        source_includes: list[str] | None = None,
        sort: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Источники найденных документов."""

    @abstractmethod
    async def search_after(
        self,
        index: str,
        query: dict[str, Any],
        *,
        size: int,
        sort: list[dict[str, Any]],
        source_includes: list[str] | None = None,
        search_after: list[Any] | None = None,
    ) -> tuple[list[dict[str, Any]], list[Any] | None]:
        """
        Страница результатов и курсор для следующей страницы.

        search_after=None в ответе означает, что данных больше нет.
        """

    @abstractmethod
    async def mget(
        self,
        index: str,
        ids: list[str],
        *,
        source_includes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Источники найденных документов, пропуская отсутствующие."""
