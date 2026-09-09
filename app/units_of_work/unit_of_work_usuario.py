from fastapi import Depends

from app.database.connection import get_session
from app.repository.usuarios_repository import UsuarioRepository
from sqlalchemy.orm import Session

class UnitOfWork:
    def __init__(self, banco: Session):
        self.banco = banco

        self.usuarios = UsuarioRepository(self.banco)

def get_uow(banco: Session = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(banco)