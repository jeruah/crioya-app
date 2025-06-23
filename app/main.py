from fastapi import FastAPI

from .routers import pages, pedido, clientes, facturas
from .database import create_db_and_tables

app = FastAPI()


app.include_router(pages.router)
app.include_router(pedido.router)
app.include_router(clientes.router)
app.include_router(facturas.router)

create_db_and_tables()