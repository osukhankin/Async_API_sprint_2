import pytest
import pytest_asyncio

from testdata.es_mapping import ES_GENRES_INDEX_MAPPING
from testdata.films import (
    FILM_DETAIL_ID,
    GENRE_ACTION_ID,
    UNKNOWN_FILM_ID,
    UNKNOWN_GENRE_ID,
    films_for_films,
    genres_for_films,
    make_film,
    make_genre,
)


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def prepare_films_data(es_write_data, redis_client):
    await redis_client.flushdb()
    await es_write_data(films_for_films())
    await es_write_data(
        genres_for_films(),
        index='genres',
        mapping=ES_GENRES_INDEX_MAPPING,
    )


@pytest.mark.parametrize(
    'film_id, expected_answer',
    [
        (
            FILM_DETAIL_ID,
            {
                'status': 200,
                'title': 'Detail Film',
                'imdb_rating': 9.9,
                'description': 'Full film card',
            },
        ),
        (
            UNKNOWN_FILM_ID,
            {'status': 404},
        ),
        (
            'not-a-film-id',
            {'status': 404},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_film_by_id(
    make_get_request,
    film_id: str,
    expected_answer: dict,
):
    response = await make_get_request(f'/api/v1/films/{film_id}/')

    assert response.status == expected_answer['status']
    if expected_answer['status'] != 200:
        return

    assert response.body['uuid'] == film_id
    assert response.body['title'] == expected_answer['title']
    assert response.body['imdb_rating'] == expected_answer['imdb_rating']
    assert response.body['description'] == expected_answer['description']
    assert response.body['genre']
    assert response.body['actors']
    assert response.body['directors']
    assert response.body['writers']
    assert response.body['genre'][0]['uuid'] == GENRE_ACTION_ID
    assert response.body['genre'][0]['name'] == 'Action'
    assert response.body['actors'][0]['full_name'] == 'Ann'


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        # page_size по умолчанию = 50
        (
            {},
            {'status': 200, 'length': 50},
        ),
        (
            {'page_size': 1},
            {'status': 200, 'length': 1},
        ),
        (
            {'page_size': 10},
            {'status': 200, 'length': 10},
        ),
        (
            {'page_size': 100},
            {'status': 200, 'length': 60},
        ),
        (
            {'page_size': 10, 'page_number': 2},
            {'status': 200, 'length': 10},
        ),
        (
            {'page_size': 10, 'page_number': 7},
            {'status': 200, 'length': 0},
        ),
        # сортировка по убыванию рейтинга
        (
            {'sort': '-imdb_rating', 'page_size': 1},
            {'status': 200, 'length': 1, 'title': 'Detail Film'},
        ),
        # сортировка по возрастанию рейтинга
        (
            {'sort': 'imdb_rating', 'page_size': 1},
            {'status': 200, 'length': 1, 'title': 'Low Rating Film'},
        ),
        # фильтр по жанру Action: Detail + High + 29 List Film even = 31
        (
            {'genre': GENRE_ACTION_ID, 'page_size': 100},
            {'status': 200, 'length': 31},
        ),
        # неизвестный жанр
        (
            {'genre': UNKNOWN_GENRE_ID},
            {'status': 200, 'length': 0},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_films_list(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/films/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']
    if 'title' in expected_answer:
        assert response.body[0]['title'] == expected_answer['title']


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        (
            {'page_size': 0},
            {'status': 422},
        ),
        (
            {'page_size': -1},
            {'status': 422},
        ),
        (
            {'page_size': 101},
            {'status': 422},
        ),
        (
            {'page_size': 'abc'},
            {'status': 422},
        ),
        (
            {'page_number': 0},
            {'status': 422},
        ),
        (
            {'page_number': -1},
            {'status': 422},
        ),
        (
            {'page_number': 'abc'},
            {'status': 422},
        ),
        (
            {'page_size': 10, 'page_number': 10001},
            {'status': 422},
        ),
        (
            {'sort': 'title'},
            {'status': 422},
        ),
        (
            {'sort': 'rating'},
            {'status': 422},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_validation(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/films/', query_data)

    assert response.status == expected_answer['status']


def _film_cache_key(film_id: str) -> str:
    return f'film:{film_id}'


def _films_list_cache_key(
    page_number: int = 1,
    page_size: int = 50,
    sort: str = '-imdb_rating',
    genre: str | None = None,
) -> str:
    return (
        f'films:list:genre={genre or ""}'
        f':sort={sort}'
        f':page_number={page_number}'
        f':page_size={page_size}'
    )


async def _prepare_list_cache_probe(es_upsert_data, title: str) -> tuple[dict, dict, dict]:
    genre = make_genre(name=f'{title} Genre', description=f'{title} genre')
    film = make_film(title=title, genres=[genre['name']], imdb_rating=8.0)
    await es_upsert_data([genre], index='genres')
    await es_upsert_data([film])
    query = {'genre': genre['id'], 'page_size': 10}
    return film, genre, query


async def _cleanup_list_cache_probe(
    es_delete_ids,
    redis_client,
    film: dict,
    genre: dict,
    *cache_keys: str,
):
    await es_delete_ids([film['id']])
    await es_delete_ids([genre['id']], index='genres')
    await redis_client.delete(_film_cache_key(film['id']), f"genre:{genre['id']}", *cache_keys)


@pytest.mark.asyncio(loop_scope='session')
async def test_film_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Film Cache Hit', description='detail cache hit')
    cache_key = _film_cache_key(film['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request(f"/api/v1/films/{film['id']}/")
    second = await make_get_request(f"/api/v1/films/{film['id']}/")

    assert first.status == 200
    assert second.status == 200
    assert first.body['uuid'] == film['id']
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_film_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Film Cache Stale', description='detail cache stale')
    cache_key = _film_cache_key(film['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request(f"/api/v1/films/{film['id']}/")
    assert first.status == 200
    assert first.body['title'] == film['title']

    await es_delete_ids([film['id']])

    second = await make_get_request(f"/api/v1/films/{film['id']}/")
    assert second.status == 200
    assert second.body == first.body

    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_film_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Film Cache Flush', description='detail cache flush')
    cache_key = _film_cache_key(film['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([film])

    first = await make_get_request(f"/api/v1/films/{film['id']}/")
    assert first.status == 200

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)

    second = await make_get_request(f"/api/v1/films/{film['id']}/")
    assert second.status == 404


@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film, genre, query = await _prepare_list_cache_probe(
        es_upsert_data,
        'Redis Films List Cache Hit',
    )
    cache_key = _films_list_cache_key(page_size=10, genre=genre['id'])
    await redis_client.delete(cache_key)

    first = await make_get_request('/api/v1/films/', query)
    second = await make_get_request('/api/v1/films/', query)

    assert first.status == 200
    assert second.status == 200
    assert len(first.body) == 1
    assert first.body[0]['uuid'] == film['id']
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await _cleanup_list_cache_probe(es_delete_ids, redis_client, film, genre, cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film, genre, query = await _prepare_list_cache_probe(
        es_upsert_data,
        'Redis Films List Cache Stale',
    )
    cache_key = _films_list_cache_key(page_size=10, genre=genre['id'])
    await redis_client.delete(cache_key)

    first = await make_get_request('/api/v1/films/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])

    second = await make_get_request('/api/v1/films/', query)
    assert second.status == 200
    assert len(second.body) == 1
    assert second.body == first.body

    await _cleanup_list_cache_probe(es_delete_ids, redis_client, film, genre, cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film, genre, query = await _prepare_list_cache_probe(
        es_upsert_data,
        'Redis Films List Cache Flush',
    )
    cache_key = _films_list_cache_key(page_size=10, genre=genre['id'])
    await redis_client.delete(cache_key)

    first = await make_get_request('/api/v1/films/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)

    second = await make_get_request('/api/v1/films/', query)
    assert second.status == 200
    assert len(second.body) == 0

    await _cleanup_list_cache_probe(es_delete_ids, redis_client, film, genre, cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_cache_different_keys(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film, genre, _ = await _prepare_list_cache_probe(
        es_upsert_data,
        'Redis Films List Cache Keys',
    )
    query_small = {'genre': genre['id'], 'page_size': 1}
    query_large = {'genre': genre['id'], 'page_size': 10}
    key_small = _films_list_cache_key(page_size=1, genre=genre['id'])
    key_large = _films_list_cache_key(page_size=10, genre=genre['id'])

    await redis_client.delete(key_small, key_large)

    small = await make_get_request('/api/v1/films/', query_small)
    large = await make_get_request('/api/v1/films/', query_large)

    assert small.status == 200
    assert large.status == 200
    assert len(small.body) == 1
    assert len(large.body) == 1
    assert await redis_client.exists(key_small) == 1
    assert await redis_client.exists(key_large) == 1
    assert key_small != key_large

    await _cleanup_list_cache_probe(
        es_delete_ids,
        redis_client,
        film,
        genre,
        key_small,
        key_large,
    )


@pytest.mark.asyncio(loop_scope='session')
async def test_films_list_cache_empty_result(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    genre = make_genre(name='Redis Films List Empty Genre')
    film = make_film(
        title='Redis Films List Empty Film',
        genres=[genre['name']],
        imdb_rating=8.0,
    )
    query = {'genre': genre['id'], 'page_size': 10}
    cache_key = _films_list_cache_key(page_size=10, genre=genre['id'])

    await redis_client.delete(cache_key, f"genre:{genre['id']}")
    await es_upsert_data([genre], index='genres')
    await es_delete_ids([film['id']])

    empty = await make_get_request('/api/v1/films/', query)
    assert empty.status == 200
    assert len(empty.body) == 0
    assert await redis_client.exists(cache_key) == 1

    await es_upsert_data([film])

    cached_empty = await make_get_request('/api/v1/films/', query)
    assert cached_empty.status == 200
    assert len(cached_empty.body) == 0

    await redis_client.delete(cache_key)
    after_flush = await make_get_request('/api/v1/films/', query)
    assert after_flush.status == 200
    assert len(after_flush.body) == 1
    assert after_flush.body[0]['uuid'] == film['id']

    await _cleanup_list_cache_probe(es_delete_ids, redis_client, film, genre, cache_key)
