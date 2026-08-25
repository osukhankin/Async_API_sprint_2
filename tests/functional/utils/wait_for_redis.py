import os
import time

from redis import Redis

if __name__ == '__main__':
    host = os.getenv('REDIS_HOST', '127.0.0.1')
    port = int(os.getenv('REDIS_PORT', '6379'))
    redis_client = Redis(host=host, port=port)
    while True:
        try:
            if redis_client.ping():
                break
        except Exception:
            pass
        time.sleep(1)
