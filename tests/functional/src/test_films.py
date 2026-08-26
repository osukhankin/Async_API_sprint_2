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
