from dataclasses import dataclass
import uuid

import aiohttp
import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from settings import test_settings


@dataclass
class HTTPResponse:
    body: dict | list
    status: int


@pytest_asyncio.fixture(name='es_client', scope='session', loop_scope='session')
async def es_client_fixture():
    client = AsyncElasticsearch(hosts=test_settings.es_host, verify_certs=False)
    yield client
    await client.close()


@pytest_asyncio.fixture(name='http_session', scope='session', loop_scope='session')
async def http_session_fixture():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture(name='es_write_data', loop_scope='session')
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


@pytest_asyncio.fixture(name='make_get_request', loop_scope='session')
async def make_get_request_fixture(http_session: aiohttp.ClientSession):
    async def inner(path: str, params: dict | None = None) -> HTTPResponse:
        url = test_settings.service_url.rstrip('/') + path
        async with http_session.get(url, params=params or {}) as response:
            body = await response.json()
            return HTTPResponse(body=body, status=response.status)

    return inner


@pytest.fixture(name='es_data')
def es_data_fixture() -> list[dict]:
    return [{
        'id': str(uuid.uuid4()),
        'imdb_rating': 8.5,
        'genres': ['Action', 'Sci-Fi'],
        'title': 'The Star',
        'description': 'New World',
        'directors_names': ['Stan'],
        'actors_names': ['Ann', 'Bob'],
        'writers_names': ['Ben', 'Howard'],
        'directors': [
            {'id': 'a1111111-1111-1111-1111-111111111111', 'name': 'Stan'},
        ],
        'actors': [
            {'id': 'ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95', 'name': 'Ann'},
            {'id': 'fb111f22-121e-44a7-b78f-b19191810fbf', 'name': 'Bob'},
        ],
        'writers': [
            {'id': 'caf76c67-c0fe-477e-8766-3ab3ff2574b5', 'name': 'Ben'},
            {'id': 'b45bd7bc-2e16-46d5-b125-983d356768c6', 'name': 'Howard'},
        ],
    } for _ in range(60)]


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        (
            {'query': 'The Star'},
            {'status': 200, 'length': 50},
        ),
        (
            {'query': 'Mashed potato'},
            {'status': 200, 'length': 0},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_search(
    make_get_request,
    es_write_data,
    es_data: list[dict],
    query_data: dict,
    expected_answer: dict,
):
    await es_write_data(es_data)
    response = await make_get_request('/api/v1/films/search/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']
