from fastapi import FastAPI

from .routers import pages, pedido, clientes

app = FastAPI()

app.include_router(pages.router)
app.include_router(pedido.router)
app.include_router(clientes.router)
