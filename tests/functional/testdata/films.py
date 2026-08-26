import uuid

FILM_DETAIL_ID = '11111111-1111-1111-1111-111111111111'
GENRE_ACTION_ID = '22222222-2222-2222-2222-222222222222'
GENRE_DRAMA_ID = '33333333-3333-3333-3333-333333333333'
UNKNOWN_FILM_ID = '00000000-0000-0000-0000-000000000000'
UNKNOWN_GENRE_ID = '99999999-9999-9999-9999-999999999999'


def make_film(**overrides) -> dict:
    film = {
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
    }
    film.update(overrides)
    return film


def make_genre(**overrides) -> dict:
    genre = {
        'id': str(uuid.uuid4()),
        'name': 'Action',
        'description': 'Action movies',
    }
    genre.update(overrides)
    return genre


def genres_for_films() -> list[dict]:
    return [
        make_genre(id=GENRE_ACTION_ID, name='Action', description='Action movies'),
        make_genre(id=GENRE_DRAMA_ID, name='Drama', description='Drama movies'),
    ]


def films_for_films() -> list[dict]:
    films = [
        make_film(
            id=FILM_DETAIL_ID,
            title='Detail Film',
            description='Full film card',
            imdb_rating=9.9,
            genres=['Action'],
        ),
        make_film(title='High Rating Film', imdb_rating=9.0, genres=['Action']),
        make_film(title='Low Rating Film', imdb_rating=1.0, genres=['Drama']),
    ]
    for index in range(57):
        films.append(
            make_film(
                title=f'List Film {index}',
                imdb_rating=5.0,
                genres=['Action'] if index % 2 == 0 else ['Drama'],
            ),
        )
    return films
