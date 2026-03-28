import os

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from app.routes.usuarios import UsuariosRouter
load_dotenv()

app = FastAPI(
    title=os.environ.get("api_name"),
)
app.include_router(UsuariosRouter())

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
