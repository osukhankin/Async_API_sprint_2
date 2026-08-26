import uuid


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


def films_for_search() -> list[dict]:
    films = [make_film() for _ in range(59)]
    films.append(
        make_film(
            imdb_rating=7.0,
            genres=['Comedy'],
            title='Mashed Potato',
            description='A funny dinner story',
            actors_names=['Ann'],
            writers_names=['Ben'],
            actors=[
                {'id': 'ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95', 'name': 'Ann'},
            ],
            writers=[
                {'id': 'caf76c67-c0fe-477e-8766-3ab3ff2574b5', 'name': 'Ben'},
            ],
        ),
    )
    return films
