from testdata.films import make_film


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
