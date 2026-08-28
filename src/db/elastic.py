from functools import wraps
from typing import Any, Callable, Coroutine, Optional

from elastic_transport import ConnectionError, ConnectionTimeout, TransportError
from elasticsearch import AsyncElasticsearch, NotFoundError

from core.backoff import backoff
from core.exceptions import ElasticsearchUnavailableError
from .search_engine import SearchEngine

es: Optional[AsyncElasticsearch] = None
search_engine: Optional[SearchEngine] = None

_ES_RETRY_EXCEPTIONS = (ConnectionError, ConnectionTimeout, TransportError)


def _map_elasticsearch_unavailable(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except _ES_RETRY_EXCEPTIONS as exc:
            raise ElasticsearchUnavailableError(str(exc)) from exc

    return wrapper


class ElasticSearchEngine(SearchEngine):
    def __init__(self, client: AsyncElasticsearch):
        self._client = client

    @_map_elasticsearch_unavailable
    @backoff(exceptions=_ES_RETRY_EXCEPTIONS)
    async def get(self, index: str, doc_id: str) -> dict[str, Any] | None:
        try:
            doc = await self._client.get(index=index, id=doc_id)
        except NotFoundError:
            return None
        return dict(doc['_source'])

    @_map_elasticsearch_unavailable
    @backoff(exceptions=_ES_RETRY_EXCEPTIONS)
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
        search_kwargs: dict[str, Any] = {
            'index': index,
            'query': query,
            'from_': from_,
            'size': size,
        }
        if source_includes:
            search_kwargs['source_includes'] = source_includes
        if sort:
            search_kwargs['sort'] = sort

        docs = await self._client.search(**search_kwargs)
        return [hit['_source'] for hit in docs['hits']['hits']]

    @_map_elasticsearch_unavailable
    @backoff(exceptions=_ES_RETRY_EXCEPTIONS)
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
        search_kwargs: dict[str, Any] = {
            'index': index,
            'query': query,
            'size': size,
            'sort': sort,
        }
        if source_includes:
            search_kwargs['source_includes'] = source_includes
        if search_after is not None:
            search_kwargs['search_after'] = search_after

        docs = await self._client.search(**search_kwargs)
        hits = docs['hits']['hits']
        sources = [hit['_source'] for hit in hits]
        if len(hits) < size:
            return sources, None
        return sources, hits[-1]['sort']

    @_map_elasticsearch_unavailable
    @backoff(exceptions=_ES_RETRY_EXCEPTIONS)
    async def mget(
        self,
        index: str,
        ids: list[str],
        *,
        source_includes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        mget_kwargs: dict[str, Any] = {
            'index': index,
            'ids': ids,
        }
        if source_includes:
            mget_kwargs['source_includes'] = source_includes

        docs = await self._client.mget(**mget_kwargs)
        return [
            doc['_source']
            for doc in docs['docs']
            if doc.get('found')
        ]


async def get_search_engine() -> SearchEngine:
    return search_engine
