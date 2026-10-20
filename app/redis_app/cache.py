import json
import logging
from typing import Any, Optional

from redis.exceptions import RedisError

from .connection import get_redis_client

logger = logging.getLogger(__name__)

def gerar_chave_cache(prefixo: str, **params) -> str:
    """Gera chave única para cache baseada nos parâmetros"""
    partes = [prefixo]
    for k, v in sorted(params.items()):
        if v is not None and v != "":
            partes.append(f"{k}:{str(v)}")
    return ":".join(partes)

def buscar_cache(chave: str) -> Optional[Any]:
    """Busca dados no cache Redis"""
    r = get_redis_client()
    if not r:
        return None
    
    try:
        dados = r.get(chave)
        if dados:
            return json.loads(dados)
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Falha ao decodificar JSON do cache para chave {chave}: {e}")
        return None
    except RedisError as e:
        logger.error(f"Erro no Redis ao buscar chave {chave}: {e}")
        return None

def buscar_cache_bruto(chave: str) -> Optional[str]:
    """
    Busca os dados no cache Redis retornando a string JSON crua.
    Essencial para o TCC: Evita o custo de CPU do json.loads() em large payloads.
    """
    r = get_redis_client()
    if not r:
        return None
    
    try:
        dados = r.get(chave)
        if dados:
            # retorna bytes decodificamos para string pura
            return dados.decode('utf-8') if isinstance(dados, bytes) else dados
        return None
    except RedisError as e:
        logger.error(f"Erro no Redis ao buscar chave bruta {chave}: {e}")
        return None

def salvar_cache(chave: str, dados: Any, ttl: int = 1800) -> bool:
    """Salva dados no cache Redis. TTL padrão de 30 minutos (1800s)."""
    r = get_redis_client()
    if not r:
        return False
    
    try:
        dados_str = json.dumps(dados, default=str)
        r.setex(chave, ttl, dados_str)
        return True
    except TypeError as e:
        logger.error(f"Erro de serialização ao salvar cache {chave}: {e}")
        return False
    except RedisError as e:
        logger.error(f"Erro no Redis ao salvar chave {chave}: {e}")
        return False

def limpar_cache_pattern(pattern: str) -> int:
    """Limpa cache com padrão específico"""
    r = get_redis_client()
    if not r:
        return 0
    
    try:
        chaves = list(r.scan_iter(match=pattern))
        if not chaves:
            return 0
        
        total_deletado = 0
        tamanho_lote = 500
        
        for i in range(0, len(chaves), tamanho_lote):
            lote = chaves[i:i + tamanho_lote]
            total_deletado += r.delete(*lote)
            
        return total_deletado
    except RedisError as e:
        logger.error(f"Erro no Redis ao limpar pattern {pattern}: {e}")
        return 0

def limpar_cache(chave: str) -> bool:
    """Remove uma chave específica do cache"""
    r = get_redis_client()
    if not r:
        return False
    
    try:
        return bool(r.delete(chave))
    except RedisError as e:
        logger.error(f"Erro no Redis ao limpar chave {chave}: {e}")
        return False