import aiohttp
import pytest_asyncio
from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk
from redis.asyncio import Redis

from settings import test_settings
from utils.helpers import HTTPResponse


@pytest_asyncio.fixture(name='es_client', scope='session', loop_scope='session')
async def es_client_fixture():
    client = AsyncElasticsearch(hosts=test_settings.es_host, verify_certs=False)
    yield client
    await client.close()


@pytest_asyncio.fixture(name='redis_client', scope='session', loop_scope='session')
async def redis_client_fixture():
    client = Redis(host=test_settings.redis_host, port=test_settings.redis_port)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(name='http_session', scope='session', loop_scope='session')
async def http_session_fixture():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name='es_write_data', scope='session', loop_scope='session')
async def es_write_data_fixture(es_client: AsyncElasticsearch):
    async def inner(
        data: list[dict],
        *,
        index: str | None = None,
        mapping: dict | None = None,
    ):
        target_index = index or test_settings.es_index
        target_mapping = mapping or test_settings.es_index_mapping
        bulk_query = [
            {
                '_index': target_index,
                '_id': row[test_settings.es_id_field],
                '_source': row,
            }
            for row in data
        ]
        if await es_client.indices.exists(index=target_index):
            await es_client.indices.delete(index=target_index)
        await es_client.indices.create(index=target_index, **target_mapping)
        _updated, errors = await async_bulk(
            client=es_client,
            actions=bulk_query,
            refresh='wait_for',
        )
        if errors:
            raise Exception('Ошибка записи данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='es_upsert_data', scope='session', loop_scope='session')
async def es_upsert_data_fixture(es_client: AsyncElasticsearch):
    async def inner(data: list[dict], *, index: str | None = None):
        target_index = index or test_settings.es_index
        bulk_query = [
            {
                '_index': target_index,
                '_id': row[test_settings.es_id_field],
                '_source': row,
            }
            for row in data
        ]
        _updated, errors = await async_bulk(
            client=es_client,
            actions=bulk_query,
            refresh='wait_for',
        )
        if errors:
            raise Exception('Ошибка upsert данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='es_delete_ids', scope='session', loop_scope='session')
async def es_delete_ids_fixture(es_client: AsyncElasticsearch):
    async def inner(ids: list[str], *, index: str | None = None):
        target_index = index or test_settings.es_index
        for doc_id in ids:
            try:
                await es_client.delete(index=target_index, id=doc_id)
            except NotFoundError:
                pass
        await es_client.indices.refresh(index=target_index)

    return inner


@pytest_asyncio.fixture(name='make_get_request', scope='session', loop_scope='session')
async def make_get_request_fixture(http_session: aiohttp.ClientSession):
    async def inner(path: str, params: dict | None = None) -> HTTPResponse:
        url = test_settings.service_url.rstrip('/') + path
        async with http_session.get(url, params=params or {}) as response:
            body = await response.json()
            return HTTPResponse(body=body, status=response.status)

    return inner
