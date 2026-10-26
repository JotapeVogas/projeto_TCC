import json
import logging
from typing import Any, Optional

from redis.exceptions import RedisError

from .connection import get_redis_client

logger = logging.getLogger(__name__)

def gerar_chave_cache(prefixo: str, **params) -> str:
    """
    Gera uma string única formatada para atuar como chave no Redis.
    
    Parâmetros:
    - prefixo: String base que identifica o escopo do cache (ex: 'usuarios:lista').
    - params: Argumentos nomeados adicionais que serão ordenados e concatenados à chave.
    
    Lança:
    - Nenhuma exceção tratada internamente.
    
    Retorna:
    - String formatada representando a chave do cache.
    """
    partes = [prefixo]
    for k, v in sorted(params.items()):
        if v is not None and v != "":
            partes.append(f"{k}:{str(v)}")
    return ":".join(partes)

def buscar_cache(chave: str) -> Optional[Any]:
    """
    Recupera um valor do Redis e realiza o parse do JSON para objetos Python.
    
    Parâmetros:
    - chave: String exata de identificação do dado no cache.
    
    Lança:
    - Erros internos do Redis ou de decodificação são capturados e logados.
    
    Retorna:
    - O objeto Python decodificado (lista, dict, etc.) ou None se falhar/não existir.
    """
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
    Recupera um valor do Redis sem realizar a conversão via json.loads().
    
    Extremamente performático para grandes volumes, anulando o gargalo de serialização 
    CPU-bound e entregando apenas a string em complexidade O(1).
    
    Parâmetros:
    - chave: String exata de identificação do dado no cache.
    
    Lança:
    - RedisError: Capturado e logado internamente em caso de falha de conexão.
    
    Retorna:
    - String bruta contendo o payload em JSON ou None se a chave não existir.
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
    """
    Serializa objetos Python para JSON e armazena no Redis com tempo de expiração.
    
    Parâmetros:
    - chave: String de identificação única.
    - dados: Objeto a ser armazenado.
    - ttl: Tempo de vida do cache em segundos (padrão 1800s / 30 min).
    
    Lança:
    - TypeError/RedisError: Capturados e logados em caso de falha na serialização ou conexão.
    
    Retorna:
    - Booleano indicando se a operação de salvamento obteve sucesso.
    """
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
    """
    Localiza e deleta chaves em lote no Redis utilizando correspondência de padrões.
    
    Parâmetros:
    - pattern: String com curingas (ex: 'payload:usuarios:*') para busca no Redis via SCAN.
    
    Lança:
    - RedisError: Capturado e logado internamente em caso de falha.
    
    Retorna:
    - Inteiro indicando a quantidade total de chaves deletadas.
    """
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
    """
    Remove uma chave única e específica do cache Redis.
    
    Parâmetros:
    - chave: String exata da chave a ser deletada.
    
    Lança:
    - RedisError: Capturado e logado internamente em caso de falha.
    
    Retorna:
    - Booleano indicando sucesso (True) ou falha (False) na remoção.
    """
    r = get_redis_client()
    if not r:
        return False
    
    try:
        return bool(r.delete(chave))
    except RedisError as e:
        logger.error(f"Erro no Redis ao limpar chave {chave}: {e}")
        return False