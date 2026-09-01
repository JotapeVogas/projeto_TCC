from sqlalchemy.orm import Session

from models.usuarios_models import UsuarioDB

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from utils.common import manipular_excecoes

class UsuarioRepository:
    def __init__(self, banco: Session):
        self.banco = banco

    def buscar_usuarios(self, id: Optional[int], ativo: str) -> List[Any]:
        """Busca usuários com base nos filtros dinâmicos."""
        try:
            query = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id if id is not None else True,
                UsuarioDB.ativo.in_([0, 1]) if ativo == '-1' else UsuarioDB.ativo == int(ativo),
            )
            
            return query.all()
        except Exception as E:
            self.banco.rollback()
            print(f"\n--- ERRO REAL QUE ACONTECEU: {E} ---\n") # Adicione esta linha
            manipular_excecoes(E)

    def verificar_nome_existente(self, nome: str) -> bool:
        """Verifica se já existe um usuário com o nome informado."""
        try:
            result = self.banco.query(UsuarioDB.id_usuario).filter(
                UsuarioDB.nome == nome.strip()
            ).first()
            return result is not None
        except Exception as e:
            raise e

    def criar_usuario(self, dados_usuario: Dict[str, Any]) -> UsuarioDB:
        """Insere um novo usuário no banco de dados."""
        try:
            db_usuario = UsuarioDB(**dados_usuario)
            self.banco.add(db_usuario)
            self.banco.flush()
            self.banco.refresh(db_usuario)
            self.banco.commit()
            return db_usuario
        except Exception as e:
            self.banco.rollback()
            raise e

    def atualizar_usuario(self, id_usuario: int, dados_atualizados: Dict[str, Any]) -> bool:
        """Atualiza campos específicos de um usuário."""
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update(dados_atualizados)
            
            if result:
                self.banco.commit()
                return True
            return False
        except Exception as e:
            self.banco.rollback()
            raise e

    def alterar_status_usuario(self, id_usuario: int, status_ativo: int) -> bool:
        """Ativa (1) ou desativa (0) um usuário."""
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': status_ativo})
            
            if result:
                self.banco.commit()
                return True
            return False
        except Exception as e:
            self.banco.rollback()
            raise e

    def desativar_usuario_no_banco(id_usuario: int, banco: Session) -> bool:
        """
        Executa o soft delete do usuário no banco de dados.
        Retorna True se o usuário foi encontrado e desativado, e False caso contrário.
        """
        try:
            result = banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': 0})
            
            if not result:
                return False
                
            banco.commit()
            return True
            
        except Exception as e:
            banco.rollback()
            raise e