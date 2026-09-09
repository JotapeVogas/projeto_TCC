import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from app.database.connection import engine
from app.database.base import Base
from app.routes.usuarios_routes import UsuariosRouter

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=os.environ.get("api_name"),
)

@app.get("/")
def teste_raiz():
    return {"mensagem": "A API do TCC está online e respondendo!"}

app.include_router(UsuariosRouter())

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
