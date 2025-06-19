from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    return templates.TemplateResponse(
        "placeholder.html", {"request": request, "titulo": "Revisar Facturas"}
    )


@router.get("/informe", response_class=HTMLResponse)
async def informe(request: Request):
    return templates.TemplateResponse(
        "placeholder.html", {"request": request, "titulo": "Informe Financiero"}
    )
