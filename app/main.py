import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from models.usuarios_models import UsuarioDB 
from database.connection import engine
from database.base import Base
from routes.usuarios_routes import UsuariosRouter

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
