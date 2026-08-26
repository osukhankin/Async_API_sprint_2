import aiohttp
import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from redis.asyncio import Redis

from settings import test_settings
from testdata.films import films_for_search
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
    async def inner(data: list[dict]):
        bulk_query = [
            {
                '_index': test_settings.es_index,
                '_id': row[test_settings.es_id_field],
                '_source': row,
            }
            for row in data
        ]
        if await es_client.indices.exists(index=test_settings.es_index):
            await es_client.indices.delete(index=test_settings.es_index)
        await es_client.indices.create(
            index=test_settings.es_index,
            **test_settings.es_index_mapping,
        )
        _updated, errors = await async_bulk(
            client=es_client,
            actions=bulk_query,
            refresh='wait_for',
        )
        if errors:
            raise Exception('Ошибка записи данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='make_get_request', scope='session', loop_scope='session')
async def make_get_request_fixture(http_session: aiohttp.ClientSession):
    async def inner(path: str, params: dict | None = None) -> HTTPResponse:
        url = test_settings.service_url.rstrip('/') + path
        async with http_session.get(url, params=params or {}) as response:
            body = await response.json()
            return HTTPResponse(body=body, status=response.status)

    return inner


@pytest.fixture(name='es_data', scope='session')
def es_data_fixture() -> list[dict]:
    return films_for_search()
