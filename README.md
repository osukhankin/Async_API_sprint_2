https://github.com/osukhankin/Async_API_sprint_2
# Movies Async API

Асинхронный API кинотеатра на FastAPI: фильмы, жанры, персоны.  
Данные в Elasticsearch, кеш в Redis. ETL переносит данные из PostgreSQL в ES.

## Стек

- FastAPI + Uvicorn
- Elasticsearch 8, Redis 7
- PostgreSQL 16 + ETL (`postgres_to_es/`)
- Pytest (функциональные тесты)

## Быстрый старт (Docker)

Из корня репозитория:

```bash
cp .env.example .env
docker compose up -d --build
```

Поднимаются:

| Сервис | URL / порт |
|---|---|
| API | http://localhost:8000 |
| OpenAPI (Swagger) | http://localhost:8000/api/openapi |
| OpenAPI JSON | http://localhost:8000/api/openapi.json |
| Elasticsearch | http://localhost:9200 |
| Redis | localhost:6379 |
| PostgreSQL | localhost:5432 |
| ETL | в фоне, логи: `docker compose logs -f etl` |

Остановка и полный сброс данных:

```bash
docker compose down -v
```

## Локальный запуск API

Инфраструктура в Docker, приложение на хосте:

```bash
cp .env.example .env
# в .env: REDIS_HOST=127.0.0.1, ELASTIC_HOST=127.0.0.1

docker compose up -d redis elasticsearch theatre-db etl

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Для PyCharm: отметьте `src` как **Sources Root**.

## Функциональные тесты

### Локально

Нужны запущенные API, Redis и Elasticsearch (см. выше).

```bash
source .venv/bin/activate
pip install -r tests/functional/requirements.txt
pytest tests/functional/src
```

### В Docker

```bash
cd tests/functional
docker compose up --build --exit-code-from tests
```

Контейнер `tests` сам ждёт ES/Redis, ставит зависимости и запускает pytest.

## Основные эндпоинты

```
GET /api/v1/films/
GET /api/v1/films/search/?query=...
GET /api/v1/films/{uuid}/

GET /api/v1/genres/
GET /api/v1/genres/{uuid}/

GET /api/v1/persons/search/?query=...
GET /api/v1/persons/{uuid}/
GET /api/v1/persons/{uuid}/film/
```

## Структура

```
├── src/                 # FastAPI-приложение
├── postgres_to_es/      # ETL Postgres → Elasticsearch
├── tests/functional/    # Функциональные тесты
├── docker-compose.yml   # API + Redis + ES + Postgres + ETL
├── .env.example         # Пример переменных окружения
└── requirements.txt
```

Подробности по ETL: [`postgres_to_es/README.md`](postgres_to_es/README.md).
