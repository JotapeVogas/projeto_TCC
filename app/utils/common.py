from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

def manipular_excecoes(E: Exception | HTTPException | SQLAlchemyError):
    """
    Intercepta, formata e sobe exceções padronizadas para o nível superior da API.
    
    Parâmetros:
    - E: Objeto de erro capturado nos blocos try/except. Pode ser genérico, de rota ou de banco.
    
    Lança:
    - HTTPException: Sempre lança uma exceção HTTP validada para interromper a requisição 
      de forma limpa, extraindo a mensagem original do SQLAlchemy caso necessário.
      
    Retorna:
    - Nenhuma (a função sempre interrompe o fluxo com um `raise`).
    """
    if isinstance(E, HTTPException):
        raise E
    elif isinstance(E, SQLAlchemyError):
        msg = str(E.orig) if hasattr(E, "orig") else str(E)
        msg = msg.split("\n")[0]
        raise HTTPException(400, msg)
    else:
        raise HTTPException(400, str(E))