from functools import lru_cache
from typing import Optional

from fastapi import Depends
from pydantic import TypeAdapter

from core.pagination import Pagination
from db.elastic import get_search_engine
from db.search_engine import SearchEngine
from models.film import Film, FilmShort
from services.cache import CacheService, get_cache_service
from services.genre import GenreService, get_genre_service

FILMS_LIST_ADAPTER = TypeAdapter(list[FilmShort])


class FilmService:
    def __init__(
        self,
        cache: CacheService,
        search_engine: SearchEngine,
        genre_service: GenreService,
    ):
        self.cache = cache
        self.search_engine = search_engine
        self.genre_service = genre_service

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        cache_key = self._film_cache_key(film_id)
        if cached := await self.cache.get_model(cache_key, Film):
            return cached

        film_data = await self._get_film(film_id)
        if not film_data:
            return None

        film, genre_names = film_data
        film.genres = await self.genre_service.get_by_names(genre_names)
        await self.cache.set_model(cache_key, film)
        return film

    async def get_films(
        self,
        pagination: Pagination,
        sort: str,
        genre: str | None = None,
    ) -> list[FilmShort]:
        cache_key = self._films_list_cache_key(
            page_number=pagination.page_number,
            page_size=pagination.page_size,
            sort=sort,
            genre=genre,
        )
        if (cached := await self._get_films_short_from_cache(cache_key)) is not None:
            return cached

        genre_name: str | None = None
        if genre:
            found_genre = await self.genre_service.get_by_id(genre)
            if found_genre is None:
                await self._set_films_short_to_cache(cache_key, [])
                return []
            genre_name = found_genre.name

        films = await self._search_films_short(
            from_=pagination.offset,
            size=pagination.page_size,
            genre=genre_name,
            sort=sort,
        )
        await self._set_films_short_to_cache(cache_key, films)
        return films

    async def search_films(
        self,
        pagination: Pagination,
        query: str,
    ) -> list[FilmShort]:
        cache_key = self._films_search_cache_key(
            page_number=pagination.page_number,
            page_size=pagination.page_size,
            query=query,
        )
        if (cached := await self._get_films_short_from_cache(cache_key)) is not None:
            return cached

        films = await self._search_films_short(
            from_=pagination.offset,
            size=pagination.page_size,
            query=query,
        )
        await self._set_films_short_to_cache(cache_key, films)
        return films

    async def _get_film(self, film_id: str) -> tuple[Film, list[str]] | None:
        source = await self.search_engine.get('movies', film_id)
        if not source:
            return None

        source = dict(source)
        genre_names = list(source.pop('genres', None) or [])
        return Film(**source, genres=[]), genre_names

    async def _get_films_short_from_cache(self, cache_key: str) -> list[FilmShort] | None:
        return await self.cache.get_typed(cache_key, FILMS_LIST_ADAPTER)

    async def _set_films_short_to_cache(self, cache_key: str, films: list[FilmShort]) -> None:
        await self.cache.set_typed(cache_key, FILMS_LIST_ADAPTER, films)

    async def _search_films_short(
        self,
        from_: int,
        size: int,
        *,
        genre: str | None = None,
        query: str | None = None,
        sort: str | None = None,
    ) -> list[FilmShort]:
        sources = await self.search_engine.search(
            'movies',
            self._build_query(genre, query),
            from_=from_,
            size=size,
            source_includes=['id', 'title', 'imdb_rating'],
            sort=self._build_sort(sort) if sort else None,
        )
        return [FilmShort(**source) for source in sources]

    async def get_films_by_ids(self, film_ids: list[str]) -> list[FilmShort]:
        if not film_ids:
            return []

        sources = await self.search_engine.mget(
            'movies',
            film_ids,
            source_includes=['id', 'title', 'imdb_rating'],
        )
        return [FilmShort(**source) for source in sources]

    @staticmethod
    def _build_query(genre: str | None, query: str | None) -> dict:
        if genre:
            return {
                'bool': {
                    'filter': [
                        {'term': {'genres': genre}},
                    ],
                },
            }
        if query:
            return {
                'multi_match': {
                    'query': query,
                    'fields': ['title', 'description'],
                },
            }
        return {'match_all': {}}

    @staticmethod
    def _build_sort(sort: str) -> list[dict]:
        order = 'desc' if sort.startswith('-') else 'asc'
        field = sort.lstrip('-')
        return [{field: {'order': order}}]

    @staticmethod
    def _film_cache_key(film_id: str) -> str:
        return f'film:{film_id}'

    @staticmethod
    def _films_list_cache_key(
        page_number: int,
        page_size: int,
        sort: str,
        genre: str | None,
    ) -> str:
        return (
            f'films:list:genre={genre or ""}'
            f':sort={sort}'
            f':page_number={page_number}'
            f':page_size={page_size}'
        )

    @staticmethod
    def _films_search_cache_key(
        page_number: int,
        page_size: int,
        query: str,
    ) -> str:
        return (
            f'films:search:query={query}'
            f':page_number={page_number}'
            f':page_size={page_size}'
        )


@lru_cache()
def get_film_service(
        cache: CacheService = Depends(get_cache_service),
        search_engine: SearchEngine = Depends(get_search_engine),
        genre_service: GenreService = Depends(get_genre_service),
) -> FilmService:
    return FilmService(cache, search_engine, genre_service)
