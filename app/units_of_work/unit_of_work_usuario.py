from fastapi import Depends

# from database.connection import get_session
# from repository.usuarios_repository import UsuarioRepository

from app.database.connection import get_session
from app.repository.usuarios_repository import UsuarioRepository

from sqlalchemy.orm import Session

class UnitOfWork:
    def __init__(self, banco: Session):
        self.banco = banco

        self.usuarios = UsuarioRepository(self.banco)

def get_uow(banco: Session = Depends(get_session)) -> UnitOfWork:
    """
    Injeta a dependência da UnitOfWork nas rotas do FastAPI.
    
    Parâmetros:
    - banco: Sessão do banco de dados injetada automaticamente pela função get_session.
    
    Lança:
    - Nenhuma exceção tratada diretamente nesta função.
    
    Retorna:
    - Uma instância configurada e pronta para uso da classe UnitOfWork.
    """
    return UnitOfWork(banco)