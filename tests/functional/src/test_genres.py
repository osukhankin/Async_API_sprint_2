import pytest
import pytest_asyncio

from testdata.es_mapping import ES_GENRES_INDEX_MAPPING
from testdata.films import make_genre
from testdata.genres import (
    GENRE_COMEDY_ID,
    GENRE_DETAIL_ID,
    GENRES_LIST_CACHE_KEY,
    UNKNOWN_GENRE_ID,
    genres_for_genres,
)


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def prepare_genres_data(es_write_data, redis_client):
    await redis_client.flushdb()
    await es_write_data(
        genres_for_genres(),
        index='genres',
        mapping=ES_GENRES_INDEX_MAPPING,
    )


@pytest.mark.parametrize(
    'genre_id, expected_answer',
    [
        (
            GENRE_DETAIL_ID,
            {'status': 200, 'name': 'Action'},
        ),
        (
            GENRE_COMEDY_ID,
            {'status': 200, 'name': 'Comedy'},
        ),
        (
            UNKNOWN_GENRE_ID,
            {'status': 404},
        ),
        (
            'not-a-genre-id',
            {'status': 404},
        ),
        (
            '123',
            {'status': 404},
        ),
        (
            'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz',
            {'status': 404},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_genre_by_id(
    make_get_request,
    genre_id: str,
    expected_answer: dict,
):
    response = await make_get_request(f'/api/v1/genres/{genre_id}/')

    assert response.status == expected_answer['status']
    if expected_answer['status'] != 200:
        return

    assert response.body['uuid'] == genre_id
    assert response.body['name'] == expected_answer['name']
    assert 'uuid' in response.body
    assert 'name' in response.body


@pytest.mark.parametrize(
    'query_data, expected_status',
    [
        ({}, 200),
        ({'page_size': 1}, 200),
        ({'page_number': 1}, 200),
        ({'sort': '-name'}, 200),
        ({'query': 'Action'}, 200),
        ({'page_size': 0}, 200),
        ({'page_size': -1}, 200),
        ({'page_size': 'abc'}, 200),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list_validation(
    make_get_request,
    query_data: dict,
    expected_status: int,
):
    response = await make_get_request('/api/v1/genres/', query_data)

    assert response.status == expected_status
    if expected_status == 200:
        assert isinstance(response.body, list)


@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list(make_get_request):
    response = await make_get_request('/api/v1/genres/')

    assert response.status == 200
    assert len(response.body) == 5

    names = {item['name'] for item in response.body}
    assert names == {'Action', 'Comedy', 'Drama', 'Thriller', 'Sci-Fi'}

    by_id = {item['uuid']: item for item in response.body}
    assert by_id[GENRE_DETAIL_ID]['name'] == 'Action'
    assert by_id[GENRE_COMEDY_ID]['name'] == 'Comedy'

    for item in response.body:
        assert set(item.keys()) == {'uuid', 'name'}
        assert item['uuid']
        assert item['name']


def _genre_cache_key(genre_id: str) -> str:
    return f'genre:{genre_id}'


@pytest.mark.asyncio(loop_scope='session')
async def test_genre_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Genre Cache Hit', description='detail cache hit')
    cache_key = _genre_cache_key(genre['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([genre], index='genres')

    first = await make_get_request(f"/api/v1/genres/{genre['id']}/")
    second = await make_get_request(f"/api/v1/genres/{genre['id']}/")

    assert first.status == 200
    assert second.status == 200
    assert first.body['uuid'] == genre['id']
    assert first.body['name'] == genre['name']
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([genre['id']], index='genres')
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_genre_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Genre Cache Stale', description='detail cache stale')
    cache_key = _genre_cache_key(genre['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([genre], index='genres')

    first = await make_get_request(f"/api/v1/genres/{genre['id']}/")
    assert first.status == 200
    assert first.body['name'] == genre['name']

    await es_delete_ids([genre['id']], index='genres')

    second = await make_get_request(f"/api/v1/genres/{genre['id']}/")
    assert second.status == 200
    assert second.body == first.body

    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_genre_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Genre Cache Flush', description='detail cache flush')
    cache_key = _genre_cache_key(genre['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([genre], index='genres')

    first = await make_get_request(f"/api/v1/genres/{genre['id']}/")
    assert first.status == 200

    await es_delete_ids([genre['id']], index='genres')
    await redis_client.delete(cache_key)

    second = await make_get_request(f"/api/v1/genres/{genre['id']}/")
    assert second.status == 404


@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list_cache_hit(
    make_get_request,
    redis_client,
):
    await redis_client.delete(GENRES_LIST_CACHE_KEY)

    first = await make_get_request('/api/v1/genres/')
    second = await make_get_request('/api/v1/genres/')

    assert first.status == 200
    assert second.status == 200
    assert len(first.body) == 5
    assert second.body == first.body
    assert await redis_client.exists(GENRES_LIST_CACHE_KEY) == 1


@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Genres List Stale', description='list cache stale')
    await redis_client.delete(GENRES_LIST_CACHE_KEY)

    first = await make_get_request('/api/v1/genres/')
    assert first.status == 200
    assert len(first.body) == 5

    await es_upsert_data([genre], index='genres')

    second = await make_get_request('/api/v1/genres/')
    assert second.status == 200
    assert len(second.body) == 5
    assert second.body == first.body

    await es_delete_ids([genre['id']], index='genres')
    await redis_client.delete(GENRES_LIST_CACHE_KEY)


@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Genres List Flush', description='list cache flush')
    await redis_client.delete(GENRES_LIST_CACHE_KEY)
    await es_upsert_data([genre], index='genres')

    first = await make_get_request('/api/v1/genres/')
    assert first.status == 200
    assert len(first.body) == 6
    assert any(item['uuid'] == genre['id'] for item in first.body)

    await es_delete_ids([genre['id']], index='genres')
    await redis_client.delete(GENRES_LIST_CACHE_KEY)

    second = await make_get_request('/api/v1/genres/')
    assert second.status == 200
    assert len(second.body) == 5
    assert all(item['uuid'] != genre['id'] for item in second.body)


@pytest.mark.asyncio(loop_scope='session')
async def test_genres_list_cache_empty_result(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    seed = genres_for_genres()
    seed_ids = [genre['id'] for genre in seed]

    await redis_client.delete(GENRES_LIST_CACHE_KEY)
    await es_delete_ids(seed_ids, index='genres')

    empty = await make_get_request('/api/v1/genres/')
    assert empty.status == 200
    assert len(empty.body) == 0
    assert await redis_client.exists(GENRES_LIST_CACHE_KEY) == 1

    await es_upsert_data(seed, index='genres')

    cached_empty = await make_get_request('/api/v1/genres/')
    assert cached_empty.status == 200
    assert len(cached_empty.body) == 0

    await redis_client.delete(GENRES_LIST_CACHE_KEY)
    after_flush = await make_get_request('/api/v1/genres/')
    assert after_flush.status == 200
    assert len(after_flush.body) == 5
