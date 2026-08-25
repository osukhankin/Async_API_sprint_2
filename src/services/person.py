from functools import lru_cache
from typing import Optional

from fastapi import Depends
from pydantic import BaseModel, TypeAdapter

from core.pagination import Pagination
from db.elastic import get_search_engine
from db.search_engine import SearchEngine
from models.film import FilmShort
from models.person import PersonFull
from services.cache import CacheService, get_cache_service
from services.film import FilmService, get_film_service

PERSONS_LIST_ADAPTER = TypeAdapter(list[PersonFull])


class PersonFilmsCache(BaseModel):
    films: list[FilmShort] | None


class PersonService:
    def __init__(
        self,
        cache: CacheService,
        search_engine: SearchEngine,
        film_service: FilmService,
    ):
        self.cache = cache
        self.search_engine = search_engine
        self.film_service = film_service

    async def get_by_id(self, person_id: str) -> Optional[PersonFull]:
        cache_key = self._person_cache_key(person_id)
        if cached := await self.cache.get_model(cache_key, PersonFull):
            return cached

        person = await self._get_person(person_id)
        if not person:
            return None
        await self.cache.set_model(cache_key, person)
        return person

    async def search_persons(
        self,
        pagination: Pagination,
        query: str,
    ) -> list[PersonFull]:
        cache_key = self._persons_search_cache_key(
            page_number=pagination.page_number,
            page_size=pagination.page_size,
            query=query,
        )
        if (cached := await self.cache.get_typed(cache_key, PERSONS_LIST_ADAPTER)) is not None:
            return cached

        persons = await self._search_persons(
            from_=pagination.offset,
            size=pagination.page_size,
            query=query,
        )
        await self.cache.set_typed(cache_key, PERSONS_LIST_ADAPTER, persons)
        return persons

    async def get_person_films(self, person_id: str) -> list[FilmShort] | None:
        cache_key = self._person_films_cache_key(person_id)
        cached = await self.cache.get_model(cache_key, PersonFilmsCache)
        if cached is not None:
            return cached.films

        person = await self.get_by_id(person_id)
        if person is None:
            await self.cache.set_model(cache_key, PersonFilmsCache(films=None))
            return None

        films = await self.film_service.get_films_by_ids([film.id for film in person.films])
        await self.cache.set_model(cache_key, PersonFilmsCache(films=films))
        return films

    async def _get_person(self, person_id: str) -> PersonFull | None:
        source = await self.search_engine.get('persons', person_id)
        if not source:
            return None
        return PersonFull(**source)

    async def _search_persons(
        self,
        from_: int,
        size: int,
        query: str,
    ) -> list[PersonFull]:
        sources = await self.search_engine.search(
            'persons',
            {'match': {'full_name': query}},
            from_=from_,
            size=size,
        )
        return [PersonFull(**source) for source in sources]

    @staticmethod
    def _person_cache_key(person_id: str) -> str:
        return f'person:{person_id}'

    @staticmethod
    def _persons_search_cache_key(
        page_number: int,
        page_size: int,
        query: str,
    ) -> str:
        return (
            f'persons:search:query={query}'
            f':page_number={page_number}'
            f':page_size={page_size}'
        )

    @staticmethod
    def _person_films_cache_key(person_id: str) -> str:
        return f'persons:films:{person_id}'


@lru_cache()
def get_person_service(
        cache: CacheService = Depends(get_cache_service),
        search_engine: SearchEngine = Depends(get_search_engine),
        film_service: FilmService = Depends(get_film_service),
) -> PersonService:
    return PersonService(cache, search_engine, film_service)
