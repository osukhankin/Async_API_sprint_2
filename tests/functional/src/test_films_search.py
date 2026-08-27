import pytest
import pytest_asyncio

from testdata.films import make_film
from testdata.films_search import films_for_search


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def prepare_films_search_data(es_write_data, redis_client):
    await redis_client.flushdb()
    await es_write_data(films_for_search())


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        # точная фраза в title
        (
            {'query': 'The Star'},
            {'status': 200, 'length': 50},
        ),
        # частичное совпадение
        (
            {'query': 'Star'},
            {'status': 200, 'length': 50},
        ),
        # регистр
        (
            {'query': 'the star'},
            {'status': 200, 'length': 50},
        ),
        # поиск по description
        (
            {'query': 'New World'},
            {'status': 200, 'length': 50},
        ),
        # одна запись по уникальному title
        (
            {'query': 'Mashed Potato'},
            {'status': 200, 'length': 1},
        ),
        # ничего не найдено
        (
            {'query': 'Unknown Film XYZ'},
            {'status': 200, 'length': 0},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_search_by_phrase(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/films/search/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        # page_size по умолчанию = 50
        (
            {'query': 'The Star'},
            {'status': 200, 'length': 50},
        ),
        (
            {'query': 'The Star', 'page_size': 1},
            {'status': 200, 'length': 1},
        ),
        (
            {'query': 'The Star', 'page_size': 10},
            {'status': 200, 'length': 10},
        ),
        (
            {'query': 'The Star', 'page_size': 20},
            {'status': 200, 'length': 20},
        ),
        # все подходящие (59), меньше page_size
        (
            {'query': 'The Star', 'page_size': 100},
            {'status': 200, 'length': 59},
        ),
        # вторая страница
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': 2},
            {'status': 200, 'length': 10},
        ),
        # страница за пределами данных
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': 7},
            {'status': 200, 'length': 0},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_search_n_records(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/films/search/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        # нет query
        (
            {},
            {'status': 422},
        ),
        # query пустая строка
        (
            {'query': ''},
            {'status': 422},
        ),
        # page_size 0
        (
            {'query': 'The Star', 'page_size': 0},
            {'status': 422},
        ),
        # page_size -1
        (
            {'query': 'The Star', 'page_size': -1},
            {'status': 422},
        ),
        # page_size 101
        (
            {'query': 'The Star', 'page_size': 101},
            {'status': 422},
        ),
        # page_size не число
        (
            {'query': 'The Star', 'page_size': 'abc'},
            {'status': 422},
        ),
        # page_number 0
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': 0},
            {'status': 422},
        ),
        # page_number -1
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': -1},
            {'status': 422},
        ),
        # page_number не число
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': 'abc'},
            {'status': 422},
        ),
        # page_number * page_size > 10000
        (
            {'query': 'The Star', 'page_size': 10, 'page_number': 10001},
            {'status': 422},
        ),
        # query длиннее max_length
        (
            {'query': 'x' * 101},
            {'status': 422},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_search_validation(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/films/search/', query_data)

    assert response.status == expected_answer['status']


def _search_cache_key(query: str, page_number: int = 1, page_size: int = 50) -> str:
    return (
        f'films:search:query={query}'
        f':page_number={page_number}'
        f':page_size={page_size}'
    )


@pytest.mark.asyncio(loop_scope='session')
async def test_search_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Cache Hit Film', description='cache hit probe')
    query = {'query': film['title']}
    cache_key = _search_cache_key(film['title'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request('/api/v1/films/search/', query)
    second = await make_get_request('/api/v1/films/search/', query)

    assert first.status == 200
    assert second.status == 200
    assert len(first.body) == 1
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_search_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Cache Stale Film', description='cache stale probe')
    query = {'query': film['title']}
    cache_key = _search_cache_key(film['title'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request('/api/v1/films/search/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])

    second = await make_get_request('/api/v1/films/search/', query)
    assert second.status == 200
    assert len(second.body) == 1
    assert second.body == first.body

    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_search_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Cache Flush Film', description='cache flush probe')
    query = {'query': film['title']}
    cache_key = _search_cache_key(film['title'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request('/api/v1/films/search/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)

    second = await make_get_request('/api/v1/films/search/', query)
    assert second.status == 200
    assert len(second.body) == 0


@pytest.mark.asyncio(loop_scope='session')
async def test_search_cache_different_keys(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Cache Keys Film', description='cache keys probe')
    await es_upsert_data([film])

    query_small = {'query': film['title'], 'page_size': 1}
    query_large = {'query': film['title'], 'page_size': 10}
    key_small = _search_cache_key(film['title'], page_size=1)
    key_large = _search_cache_key(film['title'], page_size=10)

    await redis_client.delete(key_small, key_large)

    small = await make_get_request('/api/v1/films/search/', query_small)
    large = await make_get_request('/api/v1/films/search/', query_large)

    assert small.status == 200
    assert large.status == 200
    assert len(small.body) == 1
    assert len(large.body) == 1
    assert await redis_client.exists(key_small) == 1
    assert await redis_client.exists(key_large) == 1
    assert key_small != key_large

    await es_delete_ids([film['id']])
    await redis_client.delete(key_small, key_large)


@pytest.mark.asyncio(loop_scope='session')
async def test_search_cache_empty_result(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Cache Empty Film', description='cache empty probe')
    query = {'query': film['title']}
    cache_key = _search_cache_key(film['title'])

    await redis_client.delete(cache_key)
    await es_delete_ids([film['id']])

    empty = await make_get_request('/api/v1/films/search/', query)
    assert empty.status == 200
    assert len(empty.body) == 0
    assert await redis_client.exists(cache_key) == 1

    await es_upsert_data([film])

    cached_empty = await make_get_request('/api/v1/films/search/', query)
    assert cached_empty.status == 200
    assert len(cached_empty.body) == 0

    await redis_client.delete(cache_key)
    after_flush = await make_get_request('/api/v1/films/search/', query)
    assert after_flush.status == 200
    assert len(after_flush.body) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)
