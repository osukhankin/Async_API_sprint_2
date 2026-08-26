import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def prepare_search_data(es_write_data, es_data, redis_client):
    await redis_client.flushdb()
    await es_write_data(es_data)


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
