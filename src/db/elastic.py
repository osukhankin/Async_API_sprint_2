from typing import Any, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError

from .search_engine import SearchEngine

es: Optional[AsyncElasticsearch] = None
search_engine: Optional[SearchEngine] = None


class ElasticSearchEngine(SearchEngine):
    def __init__(self, client: AsyncElasticsearch):
        self._client = client

    async def get(self, index: str, doc_id: str) -> dict[str, Any] | None:
        try:
            doc = await self._client.get(index=index, id=doc_id)
        except NotFoundError:
            return None
        return dict(doc['_source'])

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
