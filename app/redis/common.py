from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

def manipular_excecoes(E: Exception | HTTPException | SQLAlchemyError):
    if isinstance(E, HTTPException):
        raise E
    elif isinstance(E, SQLAlchemyError):
        msg = str(E.orig) if hasattr(E, "orig") else str(E)
        msg = msg.split("\n")[0]
        raise HTTPException(400, msg)
    else:
        raise HTTPException(400, str(E))