from contextlib import contextmanager
from typing import Iterator
import json
import time

from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, status, Query, Body, Path

from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session

from pydantic import BaseModel, EmailStr, Field

from typing import Optional, List, Literal

from dotenv import load_dotenv

import redis
import os

load_dotenv()

app = FastAPI()

# =================================================================================
# CONFIGURAÇÃO E TESTE DO REDIS
# =================================================================================
print("🔧 INICIANDO CONFIGURAÇÃO REDIS...")
print(f"🔧 REDIS_HOST: {os.getenv('REDIS_HOST', 'localhost')}")
print(f"🔧 REDIS_PORT: {os.getenv('REDIS_PORT', 6379)}")
print(f"🔧 REDIS_DB: {os.getenv('REDIS_DB', 0)}")
print(f"🔧 REDIS_PASSWORD: {'***' if os.getenv('REDIS_PASSWORD') else 'None'}")

try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD") if os.getenv("REDIS_PASSWORD") else None,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    print("🔧 Cliente Redis criado, testando conexão...")
    # Teste de conexão
    ping_result = redis_client.ping()
    print(f"🔧 Ping result: {ping_result}")
    print("✅ Redis conectado com sucesso!")
    REDIS_ENABLED = True
except Exception as e:
    print(f"❌ Redis não disponível: {e}")
    print(f"❌ Tipo do erro: {type(e).__name__}")
    print("⚠️ Aplicação continuará sem cache")
    REDIS_ENABLED = False
    redis_client = None

print(f"🔧 REDIS_ENABLED final: {REDIS_ENABLED}")

# =================================================================================
# FUNÇÕES DE CACHE REDIS
# =================================================================================
def gerar_chave_cache(prefixo: str, **params) -> str:
    """Gera chave única para cache baseada nos parâmetros"""
    partes = [prefixo]
    for k, v in sorted(params.items()):
        if v is not None and v != "":
            partes.append(f"{k}:{v}")
    chave_final = ":".join(partes)
    print(f"🔑 Chave gerada: {chave_final}")
    return chave_final

def buscar_cache(chave: str):
    """Busca dados no cache Redis"""
    if not REDIS_ENABLED:
        print("⚠️ Redis desabilitado - pulando cache")
        return None
    
    try:
        print(f"🔍 CONSULTANDO REDIS: '{chave}'")
        start_time = time.time()
        
        dados = redis_client.get(chave)
        
        end_time = time.time()
        tempo_ms = (end_time - start_time) * 1000
        
        if dados:
            print(f"✅ CACHE HIT! 🚀 Redis respondeu em {tempo_ms:.2f}ms (SUPER RÁPIDO!)")
            return json.loads(dados)
        print(f"❌ CACHE MISS! 📭 Redis consultado em {tempo_ms:.2f}ms - vazio, vai pro PostgreSQL")
        return None
    except Exception as e:
        print(f"⚠️ Erro ao acessar REDIS: {e}")
        return None

def salvar_cache(chave: str, dados, ttl: int = 300):
    """Salva dados no cache Redis"""
    if not REDIS_ENABLED:
        print("⚠️ Redis desabilitado - não salvando cache")
        return
    
    try:
        start_time = time.time()
        
        redis_client.setex(chave, ttl, json.dumps(dados, default=str))
        
        end_time = time.time()
        tempo_ms = (end_time - start_time) * 1000
        
        print(f"💾 SALVO NO REDIS em {tempo_ms:.2f}ms! ⏰ Expira em {ttl}s")
    except Exception as e:
        print(f"⚠️ Erro ao salvar no REDIS: {e}")

def limpar_cache_pattern(pattern: str):
    """Limpa cache com padrão específico"""
    if not REDIS_ENABLED:
        print("⚠️ Redis desabilitado - não há cache para limpar")
        return
    
    try:
        chaves = list(redis_client.scan_iter(match=pattern))
        if chaves:
            redis_client.delete(*chaves)
            print(f"🧹 CACHE LIMPO NO REDIS! 🗑️ {len(chaves)} chaves removidas ({pattern})")
        else:
            print(f"🧹 Nenhuma chave no REDIS para limpar: {pattern}")
    except Exception as e:
        print(f"⚠️ Erro ao limpar cache no REDIS: {e}")

# Configuração do banco de dados
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo SQLAlchemy
class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    ativo = Column(Integer, nullable=False, default=1)

# Criar tabelas
Base.metadata.create_all(bind=engine)

@contextmanager
def Database() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos Pydantic
class UsuarioBase(BaseModel):
    id: Optional[int] = None
    nome: str
    email: EmailStr
    ativo: int = Field(default=1, description="1: ativo | 0: inativo")

class SetUser(UsuarioBase):
    pass

    class Config:
        from_attributes = True

# Rotas
@app.get("/", response_model=dict, 
        summary="Página inicial",
        description="Redireciona para a documentação interativa da API (Swagger UI).") 
def home():
    return {
        "message": "API CRUD com Cache Redis",
        "docs": "http://127.0.0.1:5000/docs",
        "redis_status": "Conectado" if REDIS_ENABLED else "Desconectado"
    }

@app.get("/health", summary="Health Check e Status Redis")
def health_check():
    """Verifica status da aplicação e serviços"""
    status_db = "OK"
    status_redis = "OK" if REDIS_ENABLED else "OFFLINE"
    cache_info = {}
    
    try:
        with Database() as db:
            db.execute("SELECT 1")
    except Exception:
        status_db = "ERROR"
    
    if REDIS_ENABLED:
        try:
            cache_info = {
                "total_keys": redis_client.dbsize(),
                "user_cache_keys": len(list(redis_client.scan_iter(match="usuarios:*"))),
                "redis_info": {
                    "used_memory": redis_client.info().get('used_memory_human', 'N/A'),
                    "connected_clients": redis_client.info().get('connected_clients', 'N/A')
                }
            }
        except Exception as e:
            status_redis = f"ERROR: {str(e)}"
    
    return {
        "status": "UP",
        "database": status_db,
        "redis": status_redis,
        "cache_info": cache_info
    }

@app.post("/usuarios", 
            status_code=status.HTTP_201_CREATED,
            response_model=SetUser,
            summary="Criar novo usuário",
            description="Cadastra um novo usuário no sistema.",
            responses={
                201: {"description": "Usuário criado com sucesso"},
                400: {"description": "Dados inválidos ou erro no banco de dados"}
            })
def set_user(user_info: SetUser = Body(...)):
    try:
        print("📝 POST: Criando novo usuário no POSTGRESQL...")
        start_time = time.time()
        
        new_user = UsuarioDB(**user_info.dict(exclude={"id"}))
        with Database() as banco:
            banco.add(new_user)
            banco.flush()
            banco.refresh(new_user)
            if new_user.id:
                user_info.id = new_user.id
            banco.commit()
        
        end_time = time.time()
        tempo_ms = (end_time - start_time) * 1000
        
        print(f"✅ USUÁRIO SALVO NO POSTGRESQL em {tempo_ms:.2f}ms!")
        # LIMPAR CACHE (dados mudaram!)
        limpar_cache_pattern("usuarios:*")
        
        return JSONResponse(json.loads(user_info.model_dump_json()), 201)
    except Exception as E:
        if isinstance(E, HTTPException):
            raise E
        else:
            raise HTTPException(400, str(E))

@app.get("/usuarios",
    response_model=List[SetUser],
    summary="Listar usuários",
    description="""Retorna todos os usuários cadastrados. 
                Pode ser filtrado por nome quando fornecido como parâmetro.""",
    responses={
        200: {"description": "Lista de usuários retornada com sucesso"},
        404: {"description": "Nenhum usuário encontrado"}
    })
def get_users(
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    ativo: Literal["-1", "0", "1"] = Query("-1", description="-1: todos | 0: inativos | 1: ativos"),
    nome: Optional[str] = Query(default="", description="Filtrar por nome"),
    ordenador: Literal["id", "nome", "ativo"] = Query(default="id")
):
    try:
        chave_cache = gerar_chave_cache("usuarios", 
                                       id=id, 
                                       ativo=ativo, 
                                       nome=nome, 
                                       ordenador=ordenador)
        
        # STEP 2: Perguntar pro Redis primeiro
        usuarios_cache = buscar_cache(chave_cache)
        if usuarios_cache:
            print("🏃‍♂️ RETORNANDO DO REDIS! 🚀 (PostgreSQL não foi acessado)")
            return usuarios_cache
        
        # STEP 3: Redis disse "NÃO TENHO" → ir no PostgreSQL
        print("🐘 CONSULTANDO POSTGRESQL! 📊 (Cache miss - buscando no banco)")
        start_time_db = time.time()
        
        with Database() as banco:
            query = banco.query(UsuarioDB)

            if ativo == "0":
                query = query.filter(UsuarioDB.ativo == 0)
            elif ativo == "1":
                query = query.filter(UsuarioDB.ativo == 1)

            if id and id > 0:
                query = query.filter(UsuarioDB.id == id)

            if nome:
                query = query.filter(UsuarioDB.nome.ilike(f"%{nome.strip()}%"))

            coluna_ordenacao = getattr(UsuarioDB, ordenador)
            query = query.order_by(coluna_ordenacao.asc())

            db_users = query.all()

            end_time_db = time.time()
            tempo_db_ms = (end_time_db - start_time_db) * 1000

            if not db_users:
                raise HTTPException(status_code=404, detail="Nenhum usuário encontrado")
            
            # STEP 4: Converter para dict e salvar no Redis
            usuarios_dict = [SetUser.from_orm(user).dict() for user in db_users]
            salvar_cache(chave_cache, usuarios_dict, ttl=300)  # 5 minutos
            
            print(f"📤 POSTGRESQL respondeu em {tempo_db_ms:.2f}ms! 💾 (Dados salvos no Redis)")
            print(f"⚡ COMPARAÇÃO: Redis ~1-5ms vs PostgreSQL {tempo_db_ms:.2f}ms")
            return usuarios_dict
    except Exception as E:
        if isinstance(E, HTTPException):
            raise E
        else:
            raise HTTPException(400, str(E))

@app.patch("/usuarios",
            response_model=SetUser,
            summary="Atualizar usuário",
            description="Atualiza os dados de um usuário existente pelo seu ID.",
            responses={
                200: {"description": "Usuário atualizado com sucesso"},
                400: {"description": "Dados inválidos"},
                404: {"description": "Usuário não encontrado"}
            })
def update_user(user_info: SetUser = Body(..., title="Dados do usuário para atualização")
):
    try:
        print("✏️ PATCH: Atualizando usuário no POSTGRESQL...")
        start_time = time.time()
        
        with Database() as banco:
            db_user = banco.query(UsuarioDB).filter(
                UsuarioDB.id == user_info.id
            ).update(
                user_info.model_dump(exclude_unset=True, exclude={"id"})
            )
            if db_user:
                banco.commit()
                end_time = time.time()
                tempo_ms = (end_time - start_time) * 1000
                print(f"✅ USUÁRIO ATUALIZADO NO POSTGRESQL em {tempo_ms:.2f}ms!")
                # LIMPAR CACHE (dados mudaram!)
                limpar_cache_pattern("usuarios:*")
            else:
                raise HTTPException(404, 'Usuário não encontrado')
        
        return JSONResponse(json.loads(user_info.model_dump_json()), 200)
    except Exception as E:
        if isinstance(E, HTTPException):
            raise E
        else:
            raise HTTPException(400, str(E))

@app.patch("/usuarios/{user_id}",
           response_model=dict,
           summary="Ativar usuário",
           description="Ativa um usuário pelo seu ID.",
           responses={
               200: {"description": "Usuário atualizado com sucesso"},
               400: {"description": "Dados inválidos"},
               404: {"description": "Usuário não encontrado"}
           })
def activate_user(user_id: int = Path(..., title="ID do usuário", description="ID do usuário a ser ativado")):
    try:
        print("🔄 PATCH: Ativando usuário no POSTGRESQL...")
        start_time = time.time()
        
        with Database() as banco:
            db_user = banco.query(UsuarioDB).filter(
                UsuarioDB.id == user_id
            ).update(
                {"ativo": 1}
            )
            if db_user:
                banco.commit()
                end_time = time.time()
                tempo_ms = (end_time - start_time) * 1000
                print(f"✅ USUÁRIO ATIVADO NO POSTGRESQL em {tempo_ms:.2f}ms!")
                # LIMPAR CACHE (dados mudaram!)
                limpar_cache_pattern("usuarios:*")
                return {
                    "message": "Usuário ativado com sucesso", 
                    "user_id": user_id,
                    "status": "ativo"
                }
            else:
                raise HTTPException(404, 'Usuário não encontrado')
    except Exception as E:
        if isinstance(E, HTTPException):
            raise E
        else:
            raise HTTPException(400, str(E))

@app.delete("/usuarios/{user_id}", 
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Desativar usuário",
            description="Exclui logicamente um usuário do sistema pelo seu ID.",
            responses={
                204: {"description": "Usuário removido com sucesso"},
                404: {"description": "Usuário não encontrado"},
                500: {"description": "Erro interno no servidor"}
            })
def delete_user(user_id: int = Path(..., title="ID do usuário", description="ID do usuário a ser removido")):
    try:
        print("🗑️ DELETE: Desativando usuário no POSTGRESQL...")
        start_time = time.time()
        
        with Database() as banco:
            usuario = banco.query(UsuarioDB).filter(
                UsuarioDB.id == user_id
            ).update(
                {"ativo": 0}
            )
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )
            banco.commit()
            end_time = time.time()
            tempo_ms = (end_time - start_time) * 1000
            print(f"✅ USUÁRIO DESATIVADO NO POSTGRESQL em {tempo_ms:.2f}ms!")
            
            # LIMPAR CACHE (dados mudaram!)
            limpar_cache_pattern("usuarios:*")
    except Exception as E:
        if isinstance(E, HTTPException):
            raise E
        else:
            raise HTTPException(400, str(E))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5000,
        reload=True,
        workers=1
    )
