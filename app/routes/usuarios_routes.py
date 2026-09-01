from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from fastapi.responses import JSONResponse

from units_of_work.unit_of_work_usuario import UnitOfWork, get_uow
from schemas.usuarios_schemas import ListUsuarios, Setusuario, Editusuario
from utils.common import manipular_excecoes
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
        uow: UnitOfWork = Depends(get_uow),
        id: Optional[int] = Query(None, description='Filtrar por ID'),
        ativo: Literal['-1', '0', '1'] = Query('-1', description='-1: todos | 0: inativos | 1: ativos')
    ):
        """Lista usuários do sistema com base em filtros opcionais."""
        try:
            db_usuarios = uow.usuarios.buscar_usuarios(id, ativo)
            
            model_list_usuarios = ListUsuarios.model_construct()
            if db_usuarios:
                model_list_usuarios.usuarios = [
                    ListUsuarios.Usuario.model_validate(usuario, from_attributes=True) 
                    for usuario in db_usuarios
                ]

            return JSONResponse(model_list_usuarios.model_dump(), status_code=200)
        except Exception as E:
            manipular_excecoes(E)

    def postar_usuario(self, 
        usuario_info: Setusuario = Body(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """Cria e cadastra um novo usuário no sistema."""
        try:
            if uow.usuarios.verificar_nome_existente(usuario_info.nome):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, 
                    'Já existe um usuário cadastrado com esse nome!'
                )

            dados_para_db = usuario_info.model_dump(exclude={"id_usuario"})
            novo_usuario = uow.usuarios.criar_usuario(dados_para_db)
            
            usuario_info.id_usuario = novo_usuario.id_usuario
            return JSONResponse(usuario_info.model_dump(), status_code=status.HTTP_201_CREATED)

        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)

    def atualizar_usuario(self, 
        usuario_info: Editusuario = Body(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """Atualiza campos específicos das informações de um usuário existente."""
        try:
            dados_atualizados = usuario_info.model_dump(exclude_unset=True, exclude={'id_usuario'})
            
            sucesso = uow.usuarios.atualizar_usuario(usuario_info.id_usuario, dados_atualizados)
            
            if not sucesso:
                raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuário não encontrado!')
            
            return JSONResponse({'detail': 'success'}, status_code=status.HTTP_200_OK)

        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)

    def ativar_usuario(self, 
        id_usuario: int = Path(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """Reativa um usuário previamente desativado."""
        try:
            sucesso = uow.usuarios.alterar_status_usuario(id_usuario, status_ativo=1)
            
            if not sucesso:
                raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuário não encontrado!')
            
            return JSONResponse({'detail': 'success'}, status_code=status.HTTP_200_OK)
        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)

    def deletar_usuario(self,
        id_usuario: int = Path(...), 
        uow: UnitOfWork = Depends(get_uow)
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
            sucesso = uow.usuarios.desativar_usuario_no_banco(id_usuario, self.banco)
            
            if not sucesso:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail='Usuário não encontrado'
                )
            
            return JSONResponse({'detail': 'success'}, status_code=status.HTTP_200_OK)
            
        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)