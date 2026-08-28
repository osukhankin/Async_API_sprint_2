from contextlib import asynccontextmanager
from http import HTTPStatus
from logging import getLogger

from elastic_transport import ConnectionError, ConnectionTimeout, TransportError
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from api.v1 import films, genres, persons
from core.backoff import backoff
from core.config import settings
from core.exceptions import ElasticsearchUnavailableError
from db import elastic
from db import redis

logger = getLogger(__name__)

_ES_RETRY_EXCEPTIONS = (ConnectionError, ConnectionTimeout, TransportError)


@backoff(exceptions=_ES_RETRY_EXCEPTIONS)
async def _wait_for_elasticsearch(client: AsyncElasticsearch) -> None:
    if not await client.ping():
        raise ConnectionError('Elasticsearch ping returned false')


async def startup():
    redis.redis = Redis(host=settings.redis_host, port=settings.redis_port)
    redis.cache_storage = redis.RedisCacheStorage(redis.redis)
    elastic.es = AsyncElasticsearch(
        hosts=[f'{settings.elastic_schema}{settings.elastic_host}:{settings.elastic_port}'],
    )
    await _wait_for_elasticsearch(elastic.es)
    elastic.search_engine = elastic.ElasticSearchEngine(elastic.es)
    logger.info('Elasticsearch is available, application is ready')


async def shutdown():
    await redis.redis.close()
    await elastic.es.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()


app = FastAPI(
    title=settings.project_name,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    description="Информация о фильмах, жанрах и людях, участвовавших в создании произведения",
    version="1.0.0"
)


@app.exception_handler(ElasticsearchUnavailableError)
async def elasticsearch_unavailable_handler(
    request: Request,
    exc: ElasticsearchUnavailableError,
) -> ORJSONResponse:
    logger.error(
        'Elasticsearch unavailable on %s %s: %s',
        request.method,
        request.url.path,
        exc.__cause__ or exc,
        exc_info=exc,
    )
    return ORJSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        content={'detail': 'search service temporarily unavailable'},
    )


app.include_router(films.router, prefix='/api/v1/films')
app.include_router(genres.router, prefix='/api/v1/genres')
app.include_router(persons.router, prefix='/api/v1/persons')
