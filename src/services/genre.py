from functools import lru_cache
from typing import Optional

from fastapi import Depends
from pydantic import TypeAdapter

from db.elastic import get_search_engine
from db.search_engine import SearchEngine
from models.genre import Genre
from services.cache import CacheService, get_cache_service

GENRES_LIST_ADAPTER = TypeAdapter(list[Genre])
GENRES_MAX_SIZE = 1000


class GenreService:
    def __init__(self, cache: CacheService, search_engine: SearchEngine):
        self.cache = cache
        self.search_engine = search_engine

    async def get_by_id(self, genre_id: str) -> Optional[Genre]:
        cache_key = self._genre_cache_key(genre_id)
        if cached := await self.cache.get_model(cache_key, Genre):
            return cached

        genre = await self._get_genre(genre_id)
        if not genre:
            return None
        await self.cache.set_model(cache_key, genre)
        return genre

    async def _get_genre(self, genre_id: str) -> Genre | None:
        source = await self.search_engine.get('genres', genre_id)
        if not source:
            return None
        return Genre(**source)

    async def get_by_names(self, names: list[str]) -> list[Genre]:
        if not names:
            return []
        genres_by_name = {genre.name: genre for genre in await self.get_genres()}
        return [
            genres_by_name[name]
            for name in names
            if name in genres_by_name
        ]

    async def get_genres(self) -> list[Genre]:
        cache_key = 'genres:list'
        if (cached := await self._get_genres_from_cache(cache_key)) is not None:
            return cached

        genres = await self._search_genres()
        await self._set_genres_to_cache(cache_key, genres)
        return genres

    async def _search_genres(self) -> list[Genre]:
        sources = await self.search_engine.search(
            'genres',
            {'match_all': {}},
            source_includes=['id', 'name', 'description'],
            size=GENRES_MAX_SIZE,
        )
        return [Genre(**source) for source in sources]

    async def _get_genres_from_cache(self, cache_key: str) -> list[Genre] | None:
        return await self.cache.get_typed(cache_key, GENRES_LIST_ADAPTER)

    async def _set_genres_to_cache(self, cache_key: str, genres: list[Genre]) -> None:
        await self.cache.set_typed(cache_key, GENRES_LIST_ADAPTER, genres)

    @staticmethod
    def _genre_cache_key(genre_id: str) -> str:
        return f'genre:{genre_id}'


@lru_cache()
def get_genre_service(
        cache: CacheService = Depends(get_cache_service),
        search_engine: SearchEngine = Depends(get_search_engine),
) -> GenreService:
    return GenreService(cache, search_engine)
