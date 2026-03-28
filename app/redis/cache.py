import json
from typing import Any, Optional

from redis.exceptions import RedisError

from .connection import get_redis_client

def gerar_chave_cache(prefixo: str, **params) -> str:
    """Gera chave única para cache baseada nos parâmetros"""
    partes = [prefixo]
    for k, v in sorted(params.items()):
        if v is not None and v != "":
            partes.append(f"{k}:{v}")
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
    except Exception:
        return None

def salvar_cache(chave: str, dados: Any, ttl: int = None) -> bool:
    """Salva dados no cache Redis"""
    r = get_redis_client()
    if not r:
        return False
    
    try:
        if not ttl:
            ttl = 1800
        r.setex(chave, ttl, json.dumps(dados, default=str))
        return True
    except Exception:
        return False

def limpar_cache_pattern(pattern: str) -> int:
    """Limpa cache com padrão específico"""
    r = get_redis_client()
    if not r:
        return 0
    
    try:
        chaves = list(r.scan_iter(match=pattern))
        if chaves:
            return r.delete(*chaves)
        return 0
    except Exception:
        return 0

def limpar_cache(chave: str) -> bool:
    """Remove uma chave específica do cache"""
    r = get_redis_client()
    if not r:
        return False
    
    try:
        return bool(r.delete(chave))
    except Exception:
        return False