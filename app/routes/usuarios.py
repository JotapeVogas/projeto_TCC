from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from utils.common import manipular_excecoes
from app.database.connection import get_session
from app.models.usuarios import UsuarioDB
from app.schemas.usuarios import ListUsuarios, Setusuario, Editusuario

class UsuariosRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/usuarios")

        self.add_api_route('', 
                           self.buscar_usuarios, 
                           methods=['GET'], 
                           response_model=ListUsuarios, 
                           summary='Listar usuários'
        )

        self.add_api_route('', 
                           self.postar_usuario, 
                           methods=['POST'], 
                           status_code=status.HTTP_201_CREATED, 
                           response_model=Setusuario, 
                           summary='Criar novo usuário'
        )

        self.add_api_route('', 
                           self.atualizar_usuario, 
                           methods=['PATCH'], 
                           response_model=Editusuario, 
                           summary='Atualizar usuário'
        )

        self.add_api_route('/{id_usuario}/ativar', 
                           self.ativar_usuario, 
                           methods=['PATCH'], 
                           summary='Ativar usuário'
        )

        self.add_api_route('/{id_usuario}', 
                           self.deletar_usuario, 
                           methods=['DELETE'], 
                           status_code=status.HTTP_200_OK, 
                           summary='Desativar usuário'
        )

    def buscar_usuarios(self,
        banco: Session = Depends(get_session),
        id: Optional[int] = Query(None, description='Filtrar por ID'),
        ativo: Literal['-1', '0', '1'] = Query('-1', description='-1: todos | 0: inativos | 1: ativos'),
        nome: Optional[str] = Query(default='', description='Filtrar por nome'),
        ordenador: Literal['id_usuario', 'nome', 'ativo'] = Query(default='id_usuario')
    ):
        """
        Lista usuários do sistema com base em filtros opcionais.
        
        Parâmetros:
        - banco: Sessão do banco de dados (injeção de dependência).
        - id: Identificador único do usuário para filtro exato.
        - ativo: Filtro de status (-1: todos, 0: inativos, 1: ativos).
        - nome: Filtro parcial (ilike) pelo nome do usuário.
        - ordenador: Campo pelo qual a ordenação será aplicada.
        
        Retorna:
        - JSONResponse contendo o mapeamento de ListUsuarios.
        """
        try:
            #gerar chave
            model_list_usuarios = ListUsuarios.model_construct()
            # if buscar_cache(gerar chave):
            #     return JSONResponse(buscar_cache(gerar chave), status_code=200)
            # Busca otimizada com filtros dinâmicos
            db_usuarios = banco.query(UsuarioDB).filter(
                UsuarioDB.nome.ilike(f'%{nome.strip()}%') if nome else True,
                UsuarioDB.id_usuario == id if id is not None else True,
                UsuarioDB.ativo.in_([0, 1]) if ativo == '-1' else UsuarioDB.ativo == int(ativo),
            ).order_by(getattr(UsuarioDB, ordenador)).all()

            if db_usuarios:
                model_list_usuarios.usuarios = [
                    ListUsuarios.Usuario.model_validate(usuario, from_attributes=True) 
                    for usuario in db_usuarios
                ]

            #SALVAR_CACHE(gerar chave, model_list_usuarios.model_dump(), 300)
            # Retorno limpo sem loads(dump_json)
            return JSONResponse(model_list_usuarios.model_dump(), status_code=200)
        except HTTPException: 
            raise
        except Exception as E:
            banco.rollback()
            manipular_excecoes(E)

    def postar_usuario(self, 
                       usuario_info: Setusuario = Body(...), 
                       banco: Session = Depends(get_session)
    ):
        """
        Cria e cadastra um novo usuário no sistema.
        
        Parâmetros:
        - usuario_info: Model (Setusuario) Pydantic contendo os dados do novo usuário;
        - banco: Sessão do banco de dados (injeção de dependência).
        
        Lança:
        - HTTPException 400 se já existir o usuário cadastrado pelo nome.
        
        Retorna:
        - Um JSONResponse com as informações cadastradas do usuário.
        """
        try:
            # 1. Verificação de existência (apenas ID para performance)
            if banco.query(UsuarioDB.id_usuario).filter(UsuarioDB.nome == usuario_info.nome.strip()).first():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Já existe um usuário cadastrado com esse nome!')

            # 2. Inserção
            dados_para_db = usuario_info.model_dump(exclude={"id_usuario"})
            db_usuario = UsuarioDB(**dados_para_db)
            


            banco.add(db_usuario)
            banco.flush()  # Garante que o ID seja gerado para o novo usuário
            banco.refresh(db_usuario)
            
            if db_usuario.id_usuario:
                usuario_info.id_usuario = db_usuario.id_usuario
                banco.commit()
            
            # 3. Retorno
            return JSONResponse(usuario_info.model_dump(), status_code=status.HTTP_201_CREATED)

        except HTTPException: 
            raise
        except Exception as E:
            banco.rollback()
            manipular_excecoes(E)

    def atualizar_usuario(self, usuario_info: Editusuario = Body(...), 
                       banco: Session = Depends(get_session)
    ):
        """
        Atualiza campos específicos das informações de um usuário existente.
        
        Parâmetros:
        - usuario_info: Model (Editusuario) Pydantic contento os campos a alterar e o id_usuario.
        - banco: Sessão do banco de dados (injeção de dependência).
        
        Lança:
        - HTTPException 404 caso o id do usuário não seja encontrado.
        
        Retorna:
        - Um JSONResponse confirmando o sucesso do update.
        """
        try:
            # Update direto com dicionário excluindo campos vazios
            stmt = banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == usuario_info.id_usuario
            )
            
            result = stmt.update(usuario_info.model_dump(exclude_unset=True, exclude={'id_usuario'}))
            
            if not result:
                raise HTTPException(404, 'Usuário não encontrado!')
            
            banco.commit()
            return JSONResponse({'detail': 'success'}, 200)

        except HTTPException: 
            raise
        except Exception as E:
            banco.rollback()
            manipular_excecoes(E)

    def ativar_usuario(self, id_usuario: int = Path(...), 
                         banco: Session = Depends(get_session)
    ):
        """
        Reativa um usuário previamente desativado configurando o campo `ativo` para 1.
        
        Parâmetros:
        - id_usuario: O identificador (ID) do usuário no path.
        - banco: Sessão do banco de dados (injeção de dependência).
        
        Lança:
        - HTTPException 404 caso o usuário não seja encontrado.
        
        Retorna:
        - Um JSONResponse confirmando a ativação.
        """
        try:
            result = banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': 1})
            
            if not result:
                raise HTTPException(404, 'Usuário não encontrado!')
            
            banco.commit()
            return JSONResponse({'detail': 'success'}, 200)
        except HTTPException: 
            raise
        except Exception as E:
            banco.rollback()
            manipular_excecoes(E)

    def deletar_usuario(self, id_usuario: int = Path(...), 
                       banco: Session = Depends(get_session)
    ):
        """
        Realiza a desativação de um usuário (Soft Delete) definindo seu status como inativo.
        
        Parâmetros:
        - id_usuario: O identificador (ID) do usuário no path.
        - banco: Sessão do banco de dados (injeção de dependência).
        
        Lança:
        - HTTPException 404 caso o usuário não seja encontrado.
        
        Retorna:
        - Um JSONResponse confirmando a desativação.
        """
        try:
            # Exclusão lógica (Soft Delete)
            result = banco.query(UsuarioDB).filter(
                UsuarioDB.id_usuario == id_usuario
            ).update({'ativo': 0})
            
            if not result:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Usuário não encontrado')
            
            banco.commit()
            return JSONResponse({'detail': 'success'}, 200)
        except HTTPException: 
            raise
        except Exception as E:
            banco.rollback()
            manipular_excecoes(E)