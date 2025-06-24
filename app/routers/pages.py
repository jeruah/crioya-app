from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..config import templates, render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render_template(request, "index.html")


@router.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return render_template(request, "main.html")


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    """Vista para revisar facturas guardadas."""
    return render_template(
        request,
        "facturas.html",
        {"titulo": "Revisar Facturas"},
    )


@router.get("/informe", response_class=HTMLResponse)
async def informe(request: Request):
    return render_template(
        request,
        "placeholder.html",
        {"titulo": "Informe Financiero"},
    )
