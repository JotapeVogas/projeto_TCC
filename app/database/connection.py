import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"

if USE_POSTGRES:
    url_object = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )
    connect_args = {}
else:
    url_object = URL.create(
        drivername="sqlite",
        database="./fastapi_app.db",
    )
    connect_args = {"check_same_thread": False}

engine = create_engine(url_object, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    """
    Gera e gerencia o ciclo de vida de uma sessão do banco de dados (SQLAlchemy).
    
    Garante o commit automático em caso de sucesso da requisição e aplica um 
    rollback seguro para evitar transações presas em caso de falhas, fechando 
    a conexão de forma limpa ao final do uso.
    
    Parâmetros:
    - Nenhum.
    
    Lança:
    - Exception: Repassa qualquer erro ocorrido durante a transação de banco 
      para o nível superior (rotas) após efetuar o rollback.
    
    Retorna:
    - Um gerador (Generator) contendo a sessão (Session) ativa do banco de dados.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
