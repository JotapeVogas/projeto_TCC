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
        Busca usuários no banco de dados aplicando filtros dinâmicos.
        
        Parâmetros:
        - id: Identificador opcional do usuário.
        - ativo: Filtro de status ('-1' para todos, '0' para inativos, '1' para ativos).
        - quantidade: Limite numérico de registros a serem retornados (usado no ORM via .limit()).
        
        Lança:
        - Exception genérica repassada ao manipulador global após efetuar rollback.
        
        Retorna:
        - Uma lista contendo os objetos de modelo (UsuarioDB) encontrados no banco.
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
        Verifica a existência de um nome de usuário cadastrado.
        
        Parâmetros:
        - nome: String contendo o nome do usuário a ser verificado.
        
        Lança:
        - Exception genérica em caso de erro na execução da consulta.
        
        Retorna:
        - Booleano (True se o nome já existir, False caso contrário).
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
        - dados_usuario: Dicionário contendo os atributos e valores do novo usuário.
        
        Lança:
        - Exception genérica em caso de falha na inserção do ORM.
        
        Retorna:
        - O objeto da classe UsuarioDB recém-criado e persistido.
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
        - id_usuario: Identificador do usuário que sofrerá a alteração.
        - dados_atualizados: Dicionário mapeando as colunas e os novos valores.
        
        Lança:
        - Exception genérica em caso de falha no update do ORM.
        
        Retorna:
        - Booleano indicando se a atualização afetou algum registro (True) ou não (False).
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
        Altera exclusivamente a flag de ativação de um usuário.
        
        Parâmetros:
        - id_usuario: Identificador numérico do usuário.
        - status_ativo: Inteiro representando o novo status (0 para inativo, 1 para ativo).
        
        Lança:
        - Exception genérica em caso de falha no update do ORM.
        
        Retorna:
        - Booleano indicando se a alteração foi efetuada no banco (True) ou não (False).
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
        Executa a desativação lógica (Soft Delete) definindo o status como inativo (0).
        
        Parâmetros:
        - id_usuario: Identificador numérico do usuário a ser desativado.
        
        Lança:
        - Exception genérica em caso de erro na operação do ORM.
        
        Retorna:
        - Booleano indicando se o usuário foi encontrado e desativado com sucesso (True).
        """
        try:
            result = self.banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': 0})
            
            return bool(result)
        except Exception as e:
            raise e