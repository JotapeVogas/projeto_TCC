import logging
import os
import redis

logger = logging.getLogger(__name__)

def get_redis_client():
    """
    Inicializa, testa (ping) e retorna a instância de conexão com o servidor Redis.
    
    Parâmetros:
    - Nenhum. Utiliza variáveis de ambiente (.env) para carregar credenciais.
    
    Lança:
    - ConnectionError, AuthenticationError, ValueError, TypeError: Capturadas e logadas.
    
    Retorna:
    - Objeto de cliente redis.Redis ativo, ou None caso a conexão falhe.
    """
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