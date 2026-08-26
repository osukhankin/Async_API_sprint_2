from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from testdata.es_mapping import ES_MOVIES_INDEX_MAPPING


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # Как в приложении: ELASTIC_HOST в .env — только хост, не URL
    elastic_host: str = '127.0.0.1'
    elastic_port: int = 9200
    elastic_schema: str = 'http://'

    es_index: str = 'movies'
    es_id_field: str = 'id'
    es_index_mapping: dict = Field(default_factory=lambda: ES_MOVIES_INDEX_MAPPING)

    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    service_url: str = 'http://127.0.0.1:8000'

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_host(self) -> str:
        return f'{self.elastic_schema}{self.elastic_host}:{self.elastic_port}'


test_settings = TestSettings()
