from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dummy product data with emojis in the labels
PRODUCTS = {
    "papa_criolla": {
        "sizes": ["pequeña", "mediana", "grande"],
        "label": "🥔 Papa Criolla",
    },
    "papa_sabanera": {
        "sizes": ["1kg", "2kg", "5kg"],
        "label": "🥔 Papa Sabanera",
    },
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

async def _procesar_pedido(
    request: Request,
    productos: List[str],
    cantidades: List[int],
    tamanos: List[str],
):
    """Genera la respuesta con el resumen del pedido."""
    pedido = []
    for producto, cantidad, tamano in zip(productos, cantidades, tamanos):
        if cantidad <= 0:
            continue
        label = PRODUCTS.get(producto, {}).get("label", producto)
        pedido.append({
            "producto": label,
            "cantidad": cantidad,
            "tamano": tamano,
        })
    return templates.TemplateResponse(
        "pedido_resumen.html", {"request": request, "pedido": pedido}
    )


@app.get("/atencion", response_class=HTMLResponse)
async def atencion(request: Request):
    return templates.TemplateResponse(
        "pedidos.html",
        {
            "request": request,
            "products": PRODUCTS,
            "titulo": "Atenci\u00f3n al Cliente",
        },
    )


@app.post("/atencion", response_class=HTMLResponse)
async def submit_atencion(
    request: Request,
    productos: List[str] = Form(...),
    cantidades: List[int] = Form(...),
    tamanos: List[str] = Form(...),
):
    return await _procesar_pedido(request, productos, cantidades, tamanos)

@app.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "titulo": "Revisar Facturas"},
    )

@app.get("/informe", response_class=HTMLResponse)
async def informe(request: Request):
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "titulo": "Informe Financiero"},
    )


@app.get("/cocina", response_class=HTMLResponse)
async def cocina(request: Request):
    """Interfaz de cocina temporal."""
    return templates.TemplateResponse(
        "cocina.html",
        {"request": request, "titulo": "Interfaz de Cocina"},
    )
