import pytest
import pytest_asyncio

from testdata.es_mapping import ES_PERSONS_INDEX_MAPPING
from testdata.films import make_film
from testdata.persons import (
    PERSON_DETAIL_ID,
    PERSON_NO_FILMS_ID,
    PERSON_UNIQUE_ID,
    UNKNOWN_PERSON_ID,
    films_for_persons,
    make_person,
    persons_for_persons,
)


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def prepare_persons_data(es_write_data, redis_client):
    await redis_client.flushdb()
    await es_write_data(films_for_persons())
    await es_write_data(
        persons_for_persons(),
        index='persons',
        mapping=ES_PERSONS_INDEX_MAPPING,
    )


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        (
            {'query': 'Ann Detail'},
            {'status': 200, 'length': 1, 'full_name': 'Ann Detail Crew'},
        ),
        (
            {'query': 'Captain Unique'},
            {'status': 200, 'length': 1, 'full_name': 'Captain Unique Crew'},
        ),
        (
            {'query': 'Starling'},
            {'status': 200, 'length': 50},
        ),
        (
            {'query': 'Unknown Person XYZ'},
            {'status': 200, 'length': 0},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_by_phrase(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/persons/search/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']
    if 'full_name' in expected_answer:
        assert response.body[0]['full_name'] == expected_answer['full_name']
        assert response.body[0]['uuid']
        assert 'films' in response.body[0]


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        (
            {'query': 'Starling'},
            {'status': 200, 'length': 50},
        ),
        (
            {'query': 'Starling', 'page_size': 1},
            {'status': 200, 'length': 1},
        ),
        (
            {'query': 'Starling', 'page_size': 10},
            {'status': 200, 'length': 10},
        ),
        (
            {'query': 'Starling', 'page_size': 100},
            {'status': 200, 'length': 59},
        ),
        (
            {'query': 'Starling', 'page_size': 10, 'page_number': 2},
            {'status': 200, 'length': 10},
        ),
        (
            {'query': 'Starling', 'page_size': 10, 'page_number': 7},
            {'status': 200, 'length': 0},
        ),
        # все люди с общим токеном Crew: 59 + Detail + Empty + Captain = 62
        (
            {'query': 'Crew', 'page_size': 100},
            {'status': 200, 'length': 62},
        ),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_n_records(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/persons/search/', query_data)

    assert response.status == expected_answer['status']
    assert len(response.body) == expected_answer['length']


@pytest.mark.parametrize(
    'query_data, expected_answer',
    [
        ({}, {'status': 422}),
        ({'query': ''}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 0}, {'status': 422}),
        ({'query': 'Starling', 'page_size': -1}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 101}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 'abc'}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 10, 'page_number': 0}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 10, 'page_number': -1}, {'status': 422}),
        ({'query': 'Starling', 'page_size': 10, 'page_number': 'abc'}, {'status': 422}),
        (
            {'query': 'Starling', 'page_size': 10, 'page_number': 10001},
            {'status': 422},
        ),
        ({'query': 'x' * 101}, {'status': 422}),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_validation(
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    response = await make_get_request('/api/v1/persons/search/', query_data)

    assert response.status == expected_answer['status']


@pytest.mark.parametrize(
    'person_id, expected_answer',
    [
        (
            PERSON_DETAIL_ID,
            {
                'status': 200,
                'full_name': 'Ann Detail Crew',
                'films_count': 2,
            },
        ),
        (
            PERSON_NO_FILMS_ID,
            {
                'status': 200,
                'full_name': 'Bob Empty Crew',
                'films_count': 0,
            },
        ),
        (
            PERSON_UNIQUE_ID,
            {
                'status': 200,
                'full_name': 'Captain Unique Crew',
                'films_count': 1,
            },
        ),
        (UNKNOWN_PERSON_ID, {'status': 404}),
        ('not-a-person-id', {'status': 404}),
        ('123', {'status': 404}),
        ('zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz', {'status': 404}),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_person_by_id(
    make_get_request,
    person_id: str,
    expected_answer: dict,
):
    response = await make_get_request(f'/api/v1/persons/{person_id}/')

    assert response.status == expected_answer['status']
    if expected_answer['status'] != 200:
        return

    assert response.body['uuid'] == person_id
    assert response.body['full_name'] == expected_answer['full_name']
    assert len(response.body['films']) == expected_answer['films_count']
    if expected_answer['films_count']:
        assert response.body['films'][0]['uuid']
        assert response.body['films'][0]['roles']


@pytest.mark.parametrize(
    'person_id, expected_answer',
    [
        (
            PERSON_DETAIL_ID,
            {
                'status': 200,
                'length': 2,
                'titles': {'Person Film A', 'Person Film B'},
            },
        ),
        (
            PERSON_NO_FILMS_ID,
            {'status': 200, 'length': 0},
        ),
        (
            PERSON_UNIQUE_ID,
            {
                'status': 200,
                'length': 1,
                'titles': {'Person Film A'},
            },
        ),
        (UNKNOWN_PERSON_ID, {'status': 404}),
        ('not-a-person-id', {'status': 404}),
        ('123', {'status': 404}),
    ],
)
@pytest.mark.asyncio(loop_scope='session')
async def test_person_films(
    make_get_request,
    person_id: str,
    expected_answer: dict,
):
    response = await make_get_request(f'/api/v1/persons/{person_id}/film/')

    assert response.status == expected_answer['status']
    if expected_answer['status'] != 200:
        return

    assert len(response.body) == expected_answer['length']
    if 'titles' in expected_answer:
        assert {item['title'] for item in response.body} == expected_answer['titles']
        for item in response.body:
            assert item['uuid']
            assert 'imdb_rating' in item


def _person_cache_key(person_id: str) -> str:
    return f'person:{person_id}'


def _persons_search_cache_key(query: str, page_number: int = 1, page_size: int = 50) -> str:
    return (
        f'persons:search:query={query}'
        f':page_number={page_number}'
        f':page_size={page_size}'
    )


def _person_films_cache_key(person_id: str) -> str:
    return f'persons:films:{person_id}'


@pytest.mark.asyncio(loop_scope='session')
async def test_person_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonCacheHit')
    cache_key = _person_cache_key(person['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/")
    second = await make_get_request(f"/api/v1/persons/{person['id']}/")

    assert first.status == 200
    assert second.status == 200
    assert first.body['uuid'] == person['id']
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_person_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonCacheStale')
    cache_key = _person_cache_key(person['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/")
    assert first.status == 200

    await es_delete_ids([person['id']], index='persons')

    second = await make_get_request(f"/api/v1/persons/{person['id']}/")
    assert second.status == 200
    assert second.body == first.body

    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_person_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonCacheFlush')
    cache_key = _person_cache_key(person['id'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/")
    assert first.status == 200

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key)

    second = await make_get_request(f"/api/v1/persons/{person['id']}/")
    assert second.status == 404


@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonsSearchHit')
    query = {'query': person['full_name']}
    cache_key = _persons_search_cache_key(person['full_name'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request('/api/v1/persons/search/', query)
    second = await make_get_request('/api/v1/persons/search/', query)

    assert first.status == 200
    assert second.status == 200
    assert len(first.body) == 1
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonsSearchStale')
    query = {'query': person['full_name']}
    cache_key = _persons_search_cache_key(person['full_name'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request('/api/v1/persons/search/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([person['id']], index='persons')

    second = await make_get_request('/api/v1/persons/search/', query)
    assert second.status == 200
    assert len(second.body) == 1
    assert second.body == first.body

    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonsSearchFlush')
    query = {'query': person['full_name']}
    cache_key = _persons_search_cache_key(person['full_name'])

    await redis_client.delete(cache_key)
    await es_upsert_data([person], index='persons')

    first = await make_get_request('/api/v1/persons/search/', query)
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key)

    second = await make_get_request('/api/v1/persons/search/', query)
    assert second.status == 200
    assert len(second.body) == 0


@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_cache_different_keys(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonsSearchKeys')
    await es_upsert_data([person], index='persons')

    query_small = {'query': person['full_name'], 'page_size': 1}
    query_large = {'query': person['full_name'], 'page_size': 10}
    key_small = _persons_search_cache_key(person['full_name'], page_size=1)
    key_large = _persons_search_cache_key(person['full_name'], page_size=10)

    await redis_client.delete(key_small, key_large)

    small = await make_get_request('/api/v1/persons/search/', query_small)
    large = await make_get_request('/api/v1/persons/search/', query_large)

    assert small.status == 200
    assert large.status == 200
    assert await redis_client.exists(key_small) == 1
    assert await redis_client.exists(key_large) == 1
    assert key_small != key_large

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(key_small, key_large)


@pytest.mark.asyncio(loop_scope='session')
async def test_persons_search_cache_empty_result(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonsSearchEmpty')
    query = {'query': person['full_name']}
    cache_key = _persons_search_cache_key(person['full_name'])

    await redis_client.delete(cache_key)
    await es_delete_ids([person['id']], index='persons')

    empty = await make_get_request('/api/v1/persons/search/', query)
    assert empty.status == 200
    assert len(empty.body) == 0
    assert await redis_client.exists(cache_key) == 1

    await es_upsert_data([person], index='persons')

    cached_empty = await make_get_request('/api/v1/persons/search/', query)
    assert cached_empty.status == 200
    assert len(cached_empty.body) == 0

    await redis_client.delete(cache_key)
    after_flush = await make_get_request('/api/v1/persons/search/', query)
    assert after_flush.status == 200
    assert len(after_flush.body) == 1

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key)


@pytest.mark.asyncio(loop_scope='session')
async def test_person_films_cache_hit(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Person Films Hit Movie', imdb_rating=6.5)
    person = make_person(
        full_name='XyzzyPersonFilmsHit',
        films=[{'id': film['id'], 'roles': ['actor']}],
    )
    cache_key = _person_films_cache_key(person['id'])

    await redis_client.delete(cache_key, _person_cache_key(person['id']))
    await es_upsert_data([film])
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    second = await make_get_request(f"/api/v1/persons/{person['id']}/film/")

    assert first.status == 200
    assert second.status == 200
    assert len(first.body) == 1
    assert first.body[0]['uuid'] == film['id']
    assert second.body == first.body
    assert await redis_client.exists(cache_key) == 1

    await es_delete_ids([film['id']])
    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key, _person_cache_key(person['id']))


@pytest.mark.asyncio(loop_scope='session')
async def test_person_films_cache_stale_after_es_change(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Person Films Stale Movie', imdb_rating=6.5)
    person = make_person(
        full_name='XyzzyPersonFilmsStale',
        films=[{'id': film['id'], 'roles': ['actor']}],
    )
    cache_key = _person_films_cache_key(person['id'])

    await redis_client.delete(cache_key, _person_cache_key(person['id']))
    await es_upsert_data([film])
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])

    second = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert second.status == 200
    assert len(second.body) == 1
    assert second.body == first.body

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key, _person_cache_key(person['id']))


@pytest.mark.asyncio(loop_scope='session')
async def test_person_films_cache_refresh_after_flush(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    film = make_film(title='Redis Person Films Flush Movie', imdb_rating=6.5)
    person = make_person(
        full_name='XyzzyPersonFilmsFlush',
        films=[{'id': film['id'], 'roles': ['actor']}],
    )
    cache_key = _person_films_cache_key(person['id'])

    await redis_client.delete(cache_key, _person_cache_key(person['id']))
    await es_upsert_data([film])
    await es_upsert_data([person], index='persons')

    first = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert first.status == 200
    assert len(first.body) == 1

    await es_delete_ids([film['id']])
    await redis_client.delete(cache_key)

    second = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert second.status == 200
    assert len(second.body) == 0

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key, _person_cache_key(person['id']))


@pytest.mark.asyncio(loop_scope='session')
async def test_person_films_cache_empty_result(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonFilmsEmpty', films=[])
    cache_key = _person_films_cache_key(person['id'])

    await redis_client.delete(cache_key, _person_cache_key(person['id']))
    await es_upsert_data([person], index='persons')

    empty = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert empty.status == 200
    assert len(empty.body) == 0
    assert await redis_client.exists(cache_key) == 1

    film = make_film(title='Redis Person Films Empty Movie', imdb_rating=5.5)
    person_with_film = make_person(
        id=person['id'],
        full_name=person['full_name'],
        films=[{'id': film['id'], 'roles': ['actor']}],
    )
    await es_upsert_data([film])
    await es_upsert_data([person_with_film], index='persons')
    await redis_client.delete(_person_cache_key(person['id']))

    cached_empty = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert cached_empty.status == 200
    assert len(cached_empty.body) == 0

    await redis_client.delete(cache_key)
    after_flush = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert after_flush.status == 200
    assert len(after_flush.body) == 1
    assert after_flush.body[0]['uuid'] == film['id']

    await es_delete_ids([film['id']])
    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key, _person_cache_key(person['id']))


@pytest.mark.asyncio(loop_scope='session')
async def test_person_films_cache_not_found(
    make_get_request,
    es_upsert_data,
    es_delete_ids,
    redis_client,
):
    person = make_person(full_name='XyzzyPersonFilmsNotFound')
    cache_key = _person_films_cache_key(person['id'])

    await redis_client.delete(cache_key, _person_cache_key(person['id']))
    await es_delete_ids([person['id']], index='persons')

    missing = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert missing.status == 404
    assert await redis_client.exists(cache_key) == 1

    await es_upsert_data([person], index='persons')

    cached_missing = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert cached_missing.status == 404

    await redis_client.delete(cache_key)
    after_flush = await make_get_request(f"/api/v1/persons/{person['id']}/film/")
    assert after_flush.status == 200
    assert after_flush.body == []

    await es_delete_ids([person['id']], index='persons')
    await redis_client.delete(cache_key, _person_cache_key(person['id']))
