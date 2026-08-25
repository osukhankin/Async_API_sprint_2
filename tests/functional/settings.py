import os

ELASTIC_HOST = os.getenv('ELASTIC_HOST', '127.0.0.1')
ELASTIC_PORT = int(os.getenv('ELASTIC_PORT', '9200'))
ELASTIC_SCHEMA = os.getenv('ELASTIC_SCHEMA', 'http://')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
SERVICE_URL = os.getenv('SERVICE_URL', 'http://127.0.0.1:8000')
