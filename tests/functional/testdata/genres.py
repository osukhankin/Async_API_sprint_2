from testdata.films import make_genre

GENRE_DETAIL_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
GENRE_COMEDY_ID = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
GENRE_DRAMA_ID = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
GENRE_THRILLER_ID = 'dddddddd-dddd-dddd-dddd-dddddddddddd'
GENRE_SCIFI_ID = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'
UNKNOWN_GENRE_ID = '99999999-9999-9999-9999-999999999999'

GENRES_LIST_CACHE_KEY = 'genres:list'


def genres_for_genres() -> list[dict]:
    return [
        make_genre(
            id=GENRE_DETAIL_ID,
            name='Action',
            description='Action movies',
        ),
        make_genre(
            id=GENRE_COMEDY_ID,
            name='Comedy',
            description='Comedy movies',
        ),
        make_genre(
            id=GENRE_DRAMA_ID,
            name='Drama',
            description='Drama movies',
        ),
        make_genre(
            id=GENRE_THRILLER_ID,
            name='Thriller',
            description='Thriller movies',
        ),
        make_genre(
            id=GENRE_SCIFI_ID,
            name='Sci-Fi',
            description='Science fiction',
        ),
    ]
