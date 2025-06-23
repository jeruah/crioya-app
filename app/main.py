from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os

from .routers import pages, pedido, clientes, facturas
from .database import create_db_and_tables

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me"),
)


app.include_router(pages.router)
app.include_router(pedido.router)
app.include_router(clientes.router)
app.include_router(facturas.router)

create_db_and_tables()