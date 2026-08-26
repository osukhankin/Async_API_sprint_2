import time

from elasticsearch import Elasticsearch

from settings import test_settings

if __name__ == '__main__':
    es_client = Elasticsearch(hosts=test_settings.es_host)
    while True:
        try:
            if es_client.ping():
                break
        except Exception:
            pass
        time.sleep(1)
