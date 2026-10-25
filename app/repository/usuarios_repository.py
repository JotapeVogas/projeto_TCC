from sqlalchemy.orm import Session

# from models.usuarios_models import UsuarioDB
# from utils.common import manipular_excecoes

from app.models.usuarios_models import UsuarioDB
from app.utils.common import manipular_excecoes

from typing import Optional, List, Dict, Any


class UsuarioRepository:
    def __init__(self, banco: Session):
        self.banco = banco

    def buscar_usuarios(self, id: Optional[int], ativo: str, quantidade: int) -> List[Any]:
        """
        Busca usuários com base nos filtros dinâmicos de ID e status ordenados por ID.
        
        Parâmetros:
        - id: Identificador opcional do usuário.
        - ativo: Filtro de status ('-1' para todos, '0' para inativos, '1' para ativos).
        
        Lança:
        - Exceções repassadas ao manipulador global em caso de falhas na query.
        
        Retorna:
        - Uma lista contendo os registros encontrados no banco.
        """
        try:
            query = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id if id is not None else True,
                UsuarioDB.ativo.in_([0, 1]) if ativo == '-1' else UsuarioDB.ativo == int(ativo),
            ).order_by(UsuarioDB.id_usuario.asc())
            
            if quantidade > 0:
                query = query.limit(quantidade)
                
            return query.all()
        except Exception as E:
            self.banco.rollback()
            print(f"\n--- ERRO REAL QUE ACONTECEU: {E} ---\n")
            manipular_excecoes(E)

    def verificar_nome_existente(self, nome: str) -> bool:
        """
        Verifica se já existe um usuário cadastrado com o nome informado.
        
        Parâmetros:
        - nome: String contendo o nome do usuário a ser verificado.
        
        Lança:
        - Exception caso ocorra erro na execução da consulta.
        
        Retorna:
        - Um booleano (True se existir, False caso contrário).
        """
        try:
            result = self.banco.query(UsuarioDB.id_usuario).filter(
                UsuarioDB.nome == nome.strip()
            ).first()

            return result is not None
        except Exception as e:
            raise e

    def criar_usuario(self, dados_usuario: Dict[str, Any]) -> UsuarioDB:
        """
        Insere um novo registro de usuário no banco de dados.
        
        Parâmetros:
        - dados_usuario: Dicionário contendo os dados do novo usuário.
        
        Lança:
        - Exception em caso de falha na inserção, realizando o rollback.
        
        Retorna:
        - O objeto UsuarioDB recém-criado e persistido.
        """
        try:
            db_usuario = UsuarioDB(**dados_usuario)
            self.banco.add(db_usuario)
            self.banco.flush()
            self.banco.refresh(db_usuario)

            return db_usuario
        except Exception as e:
            raise e

    def atualizar_usuario(self, id_usuario: int, dados_atualizados: Dict[str, Any]) -> bool:
        """
        Atualiza campos específicos de um usuário existente.
        
        Parâmetros:
        - id_usuario: Identificador do usuário que será atualizado.
        - dados_atualizados: Dicionário com os campos e novos valores.
        
        Lança:
        - Exception em caso de erro na atualização, realizando o rollback.
        
        Retorna:
        - Um booleano indicando se a atualização foi bem-sucedida (True) ou não (False).
        """
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update(dados_atualizados)

            return bool(result)
        except Exception as e:
            raise e

    def alterar_status_usuario(self, id_usuario: int, status_ativo: int) -> bool:
        """
        Altera o status de ativação (1 para ativo, 0 para inativo) de um usuário.
        
        Parâmetros:
        - id_usuario: Identificador do usuário.
        - status_ativo: Novo valor numérico para o status (0 ou 1).
        
        Lança:
        - Exception em caso de erro, realizando o rollback.
        
        Retorna:
        - Um booleano (True se alterado com sucesso, False caso contrário).
        """
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': status_ativo})

            return bool(result)
        except Exception as e:
            raise e

    def desativar_usuario_no_banco(self, id_usuario: int) -> bool:
        """
        Executa a desativação lógica (Soft Delete) de um usuário definindo seu status como inativo.
        
        Parâmetros:
        - id_usuario: O identificador (ID) do usuário no path.
        
        Lança:
        - Exception em caso de erro na operação, realizando o rollback.
        
        Retorna:
        - Um booleano indicando se o usuário foi encontrado e desativado com sucesso.
        """
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': 0})
            
            return bool(result)
        except Exception as e:
            raise e