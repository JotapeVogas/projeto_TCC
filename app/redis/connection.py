import os
import redis

def get_redis_client():
    """Retorna cliente Redis configurado ou None se não estiver disponível"""
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            db=int(os.getenv("REDIS_DB")),
            password=os.getenv("REDIS_PASSWORD") if os.getenv("REDIS_PASSWORD") else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        r.ping()
        return r
    except Exception:
        return None