import uuid

from testdata.films import make_film

PERSON_DETAIL_ID = 'a1111111-1111-1111-1111-111111111111'
PERSON_NO_FILMS_ID = 'a2222222-2222-2222-2222-222222222222'
PERSON_UNIQUE_ID = 'a3333333-3333-3333-3333-333333333333'
UNKNOWN_PERSON_ID = '00000000-0000-0000-0000-000000000000'

PERSON_FILM_A_ID = 'b1111111-1111-1111-1111-111111111111'
PERSON_FILM_B_ID = 'b2222222-2222-2222-2222-222222222222'


def make_person(**overrides) -> dict:
    person = {
        'id': str(uuid.uuid4()),
        'full_name': 'Starling Crew',
        'films': [],
    }
    person.update(overrides)
    return person


def films_for_persons() -> list[dict]:
    return [
        make_film(
            id=PERSON_FILM_A_ID,
            title='Person Film A',
            description='First film of detail person',
            imdb_rating=8.1,
        ),
        make_film(
            id=PERSON_FILM_B_ID,
            title='Person Film B',
            description='Second film of detail person',
            imdb_rating=7.2,
        ),
    ]


def persons_for_persons() -> list[dict]:
    persons = [
        make_person(
            id=PERSON_DETAIL_ID,
            full_name='Ann Detail Crew',
            films=[
                {'id': PERSON_FILM_A_ID, 'roles': ['actor']},
                {'id': PERSON_FILM_B_ID, 'roles': ['actor', 'writer']},
            ],
        ),
        make_person(
            id=PERSON_NO_FILMS_ID,
            full_name='Bob Empty Crew',
            films=[],
        ),
        make_person(
            id=PERSON_UNIQUE_ID,
            full_name='Captain Unique Crew',
            films=[{'id': PERSON_FILM_A_ID, 'roles': ['director']}],
        ),
    ]
    for index in range(59):
        persons.append(make_person(full_name=f'Starling Crew {index}'))
    return persons
