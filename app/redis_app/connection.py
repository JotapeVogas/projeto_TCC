import logging
import os
import redis

logger = logging.getLogger(__name__)

def get_redis_client():
    """Retorna cliente Redis configurado ou None se não estiver disponível"""
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            db=int(os.getenv("REDIS_DB")),
            password=os.getenv("REDIS_PASSWORD")or None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        r.ping()
        return r
    except redis.exceptions.ConnectionError as e:
        logger.error(f"[Redis] Falha de conexão ou timeout: {e}")
        return None
    except redis.exceptions.AuthenticationError as e:
        logger.error(f"[Redis] Falha de autenticação (Senha incorreta): {e}")
        return None
    except (ValueError, TypeError) as e:
        logger.error(f"[Redis] Erro nas variáveis de ambiente (Porta ou DB não são números válidos): {e}")
        return None
    except Exception as e:
        logger.error(f"[Redis] Erro inesperado ao conectar: {e}")
        return None