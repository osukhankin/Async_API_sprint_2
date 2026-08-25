import os
import time

from elasticsearch import Elasticsearch

if __name__ == '__main__':
    host = os.getenv('ELASTIC_HOST', '127.0.0.1')
    port = os.getenv('ELASTIC_PORT', '9200')
    schema = os.getenv('ELASTIC_SCHEMA', 'http://')
    es_client = Elasticsearch(hosts=f'{schema}{host}:{port}')
    while True:
        try:
            if es_client.ping():
                break
        except Exception:
            pass
        time.sleep(1)
