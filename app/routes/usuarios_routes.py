import json
import time
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query, Body, Path
from fastapi.responses import JSONResponse

# from redis_app.cache import buscar_cache, buscar_cache_bruto, gerar_chave_cache, salvar_cache, limpar_cache_pattern, limpar_cache
# from units_of_work.unit_of_work_usuario import UnitOfWork, get_uow
# from schemas.usuarios_schemas import ListUsuarios, Setusuario, Editusuario
# from utils.common import manipular_excecoes

from app.redis_app.cache import buscar_cache, buscar_cache_bruto, gerar_chave_cache, salvar_cache, limpar_cache_pattern, limpar_cache
from app.units_of_work.unit_of_work_usuario import UnitOfWork, get_uow
from app.schemas.usuarios_schemas import ListUsuarios, Setusuario, Editusuario
from app.utils.common import manipular_excecoes

class UsuariosRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/usuarios")

        self.add_api_route('/teste', 
                           self.teste_TCC, 
                           methods=['GET'], 
                           summary='Endpoint para concluir testes para o TCC'
        )

        self.add_api_route('', 
                           self.buscar_usuarios_por_id, 
                           methods=['GET'],
                           response_model=ListUsuarios,
                           summary='Buscar usuários'
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

    def teste_TCC(self,
        uow: UnitOfWork = Depends(get_uow),
        quantidade: int = Query(0, description='Quantos registros buscar'),
        banco: Literal['Redis', 'Postgres'] = Query('Postgres', description='Escolha a origem dos dados')
    ):
        """
        Lista usuários do sistema com base em filtros opcionais, priorizando a devolução 
        direta do cache (Redis) para anular gargalos de serialização em grandes volumes.
        
        Esta rota possui telemetria embutida: o tempo exato de processamento interno 
        (CPU e I/O) é cronometrado e devolvido no payload final. Quando o dado é 
        recuperado do Redis, a API contorna o uso do json.loads e devolve uma string 
        bruta via `Response` genérico, garantindo latência mínima (O(1)).
        
        Parâmetros:
        - uow: Unidade de trabalho (UnitOfWork) injetada como dependência para acesso ao banco.
        - id: Identificador (ID) opcional do usuário para filtro.
        - ativo: Filtro de status do usuário ('-1' para todos, '0' para inativos, '1' para ativos).
        - quantidade: Opcional. Quantidade exata de registros a extrair (define o limite da query e a chave do cache).
        
        Lança:
        - Exception genérica repassada ao manipulador de exceções em caso de falhas inesperadas.
        
        Retorna:
        - Response puro (para Redis) ou JSONResponse (para PostgreSQL) contendo:
          1. "tempo_interno_ms": O tempo exato de processamento backend daquela requisição.
          2. A chave de origem ("Redis" ou "Postgres") contendo a lista dos registros solicitados.
        """
        try:
            inicio_req = time.perf_counter()

            chave_cache = f"payload:usuarios:{quantidade}"
            
            if banco == 'Redis':
                cache_bruto = buscar_cache_bruto(chave_cache) if quantidade > 0 else buscar_cache(chave_cache)
                
                if not cache_bruto:
                    return JSONResponse(
                        {"detail": "Banco está vazio. Puxe primeiro com o Postgres, depois tente novamente com o Redis."}, 
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                if quantidade > 0:
                    qtd_retornada = quantidade
                else:
                    dados_redis = json.loads(cache_bruto) if isinstance(cache_bruto, str) else cache_bruto
                    qtd_retornada = len(dados_redis.get("usuarios", []))
                
                tempo_ms = (time.perf_counter() - inicio_req) * 1000
                
                return JSONResponse({
                    "tempo_interno_ms": round(tempo_ms, 2),
                    "origem": "Redis",
                    "quantidade_retornada": qtd_retornada
                }, status_code=status.HTTP_200_OK)
            
            elif banco == 'Postgres':
                db_usuarios = uow.usuarios.buscar_usuarios(id=None, ativo='-1', quantidade=quantidade)

                qtd_retornada = len(db_usuarios) if db_usuarios else 0

                model_list_usuarios = ListUsuarios.model_construct()
                if db_usuarios:
                    model_list_usuarios.usuarios = [
                        ListUsuarios.Usuario.model_validate(usuario, from_attributes=True) 
                        for usuario in db_usuarios
                    ]

                limpar_cache_pattern("payload:usuarios:*")
                limpar_cache_pattern("usuarios:lista*")

                dados_resposta = model_list_usuarios.model_dump()
                salvar_cache(chave_cache, dados_resposta, ttl=1800)

                tempo_ms = (time.perf_counter() - inicio_req) * 1000
                
                return JSONResponse({
                    "tempo_interno_ms": round(tempo_ms, 2),
                    "origem": "Postgres",
                    "quantidade_retornada": qtd_retornada
                }, status_code=status.HTTP_200_OK)

        except Exception as E:
            manipular_excecoes(E)
        

    def buscar_usuarios_por_id(self,
        uow: UnitOfWork = Depends(get_uow),
        id: int = Query(..., description='Filtrar por ID')
    ):
        """
        Endpoint de produção para listagem de usuários.
        Filtra por ID e status de ativação diretamente no banco relacional.
        """
        try:
            db_usuarios = uow.usuarios.buscar_usuarios(id, ativo='-1', quantidade=0)

            model_list_usuarios = ListUsuarios.model_construct()
            
            if db_usuarios:
                model_list_usuarios.usuarios = [
                    ListUsuarios.Usuario.model_validate(usuario, from_attributes=True) 
                    for usuario in db_usuarios
                ]

            return model_list_usuarios

        except Exception as E:
            manipular_excecoes(E)

    def postar_usuario(self, 
        usuario_info: Setusuario = Body(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """
        Cria e cadastra um novo usuário no sistema, invalidando o cache das listagens.
        
        Parâmetros:
        - usuario_info: Objeto recebido no corpo da requisição (Body) contendo os dados de criação.
        - uow: Unidade de trabalho (UnitOfWork) injetada como dependência para acesso ao banco.
        
        Lança:
        - HTTPException 400 caso já exista um usuário cadastrado com o mesmo nome informado.
        - Exception genérica repassada ao manipulador de exceções.
        
        Retorna:
        - Um JSONResponse confirmando a criação com os dados do usuário.
        """
        try:
            if uow.usuarios.verificar_nome_existente(usuario_info.nome):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, 
                    'Já existe um usuário cadastrado com esse nome!'
                )

            dados_para_db = usuario_info.model_dump(exclude={"id_usuario"})
            novo_usuario = uow.usuarios.criar_usuario(dados_para_db)
            
            usuario_info.id_usuario = novo_usuario.id_usuario

            limpar_cache_pattern("usuarios:*")
            
            return JSONResponse(usuario_info.model_dump(), status_code=status.HTTP_201_CREATED)

        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)

    def atualizar_usuario(self, 
        usuario_info: Editusuario = Body(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """
        Atualiza campos específicos das informações de um usuário existente e limpa o cache.
        
        Parâmetros:
        - usuario_info: Objeto contendo os dados a serem atualizados e o ID do usuário (Body).
        - uow: Unidade de trabalho (UnitOfWork) injetada como dependência para acesso ao banco.
        
        Lança:
        - HTTPException 404 caso o usuário não seja encontrado para atualização.
        - Exception genérica repassada ao manipulador de exceções.
        
        Retorna:
        - Um JSONResponse confirmando o sucesso da atualização.
        """
        try:
            dados_atualizados = usuario_info.model_dump(exclude_unset=True, exclude={'id_usuario'})
            
            sucesso = uow.usuarios.atualizar_usuario(usuario_info.id_usuario, dados_atualizados)
            
            if not sucesso:
                raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuário não encontrado!')

            limpar_cache_pattern("usuarios:*")
            
            return JSONResponse({'detail': 'success'}, status_code=status.HTTP_200_OK)

        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)

    def ativar_usuario(self, 
        id_usuario: int = Path(...), 
        uow: UnitOfWork = Depends(get_uow)
    ):
        """
        Reativa um usuário previamente desativado e limpa o cache.
        
        Parâmetros:
        - id_usuario: O identificador (ID) do usuário repassado no path da requisição.
        - uow: Unidade de trabalho (UnitOfWork) injetada como dependência para acesso ao banco.
        
        Lança:
        - HTTPException 404 caso o usuário não seja encontrado.
        - Exception genérica repassada ao manipulador de exceções.
        
        Retorna:
        - Um JSONResponse confirmando a ativação.
        """
        try:
            sucesso = uow.usuarios.alterar_status_usuario(id_usuario, status_ativo=1)
            
            if not sucesso:
                raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuário não encontrado!')

            limpar_cache_pattern("usuarios:*")
            
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
        - uow: Unidade de trabalho (UnitOfWork) injetada como dependência para acesso ao banco.
        
        Lança:
        - HTTPException 404 caso o usuário não seja encontrado.
        
        Retorna:
        - Um JSONResponse confirmando a desativação.
        """
        try:
            sucesso = uow.usuarios.desativar_usuario_no_banco(id_usuario)
            
            if not sucesso:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail='Usuário não encontrado'
                )

            limpar_cache_pattern("usuarios:*")
            
            return JSONResponse({'detail': 'success'}, status_code=status.HTTP_200_OK)
            
        except HTTPException: 
            raise
        except Exception as E:
            manipular_excecoes(E)