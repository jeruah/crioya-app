from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import logging
import os

from .routers import pages, pedido, clientes, facturas
from .database import create_db_and_tables
from .errors import AppError
from . import models

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me"),
)

logging.basicConfig(level=logging.INFO)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    if request.headers.get("accept", "").startswith("text/html"):
        request.session["error"] = exc.message
        referer = request.headers.get("referer") or "/"
        return RedirectResponse(referer, status_code=302)
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logging.exception("Unhandled error: %s", exc)
    if request.headers.get("accept", "").startswith("text/html"):
        request.session["error"] = "Ocurri\u00f3 un error inesperado"
        referer = request.headers.get("referer") or "/"
        return RedirectResponse(referer, status_code=302)
    return JSONResponse({"detail": "Ocurri\u00f3 un error interno"}, status_code=500)


app.include_router(pages.router)
app.include_router(pedido.router)
app.include_router(clientes.router)
app.include_router(facturas.router)

create_db_and_tables()
