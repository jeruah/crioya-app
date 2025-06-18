import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
from geopy.geocoders import OpenCage
from geopy.distance import geodesic
import ssl
import certifi
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from . import models, database, schemas

database.create_db_and_tables()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# descomentar si se desea servir archivos estáticos
# app.mount("/static", StaticFiles(directory="static"), name="static")

ctx = ssl.create_default_context(cafile=certifi.where())
# Carta completa de productos
MENU_FORMULARIO = {
    "Entradas": [
        {"nombre": "Deditos de queso x5", "id": "deditos_queso", "precio": 8000},
        {"nombre": "Croquetas de yuca", "id": "croquetas_yuca", "precio": 6000},
        {"nombre": "Criollas crocantes", "id": "criollas_crocantes", "precio": 7000},
    ],
    "Papas familiares": [
        {"nombre": "Papas a la francesa", "id": "papas_francesas", "precio": 15000},
        {"nombre": "Papas criollas", "id": "papas_criollas", "precio": 15000},
    ],
    "Especial familiar": [
        {"nombre": "Especial familiar", "id": "especial_familiar", "precio": 28000},
    ],
    "Mixta familiar": [
        {"nombre": "Mixta familiar", "id": "mixta_familiar", "precio": 32000},
    ],
    "Crio-ya familiar": [
        {"nombre": "Crioya familiar", "id": "crioya_familiar", "precio": 35000},
    ],
    "Papas personales": [
        {"nombre": "Ranchera costeña", "id": "ranchera_costeña", "precio": 12000},
        {"nombre": "Con Costi", "id": "con_costi", "precio": 14000},
        {"nombre": "Crio-Ya", "id": "crioya", "precio": 15000},
        {"nombre": "Mexicana", "id": "mexicana", "precio": 13000},
        {"nombre": "Paisa", "id": "paisa", "precio": 14000},
    ],
    "Costillas personales": [
        {"nombre": "Costillas personales", "id": "costillas_personales", "precio": 18000},
    ],
    "Costillas para compartir": [
        {"nombre": "Costillas para compartir", "id": "costillas_compartir", "precio": 35000},
    ],
    "Hamburguesa Crioya": [
        {"nombre": "Hamburguesa Crioya", "id": "hamburguesa_crioya", "precio": 16000},
    ],
    "Perro Crioya": [
        {"nombre": "Perro Crioya", "id": "perro_crioya", "precio": 12000},
    ],
    "Menú infantil": [
        {"nombre": "Menú infantil", "id": "menu_infantil", "precio": 10000},
    ],
    "Cono": [
        {
            "nombre": "Cono 2 proteínas",
            "id": "cono_2_proteinas",
            "precio": 8000,
            "requiere_opciones": True,
            "opciones": {
                "base": ["Maíz tierno", "Madurito"],
                "proteinas": ["Chicharrón", "Costillas BBQ", "Pollo desmechado", "Carne desmechada", "Chorizo"],
            },
        },
    ],
    "Bebidas": [
        {"nombre": "Gaseosa personal", "id": "gaseosa_personal", "precio": 3000},
        {"nombre": "Gaseosa litro", "id": "gaseosa_litro", "precio": 6000},
        {"nombre": "Jugo natural en agua", "id": "jugo_agua", "precio": 4000},
        {"nombre": "Jugo natural en leche", "id": "jugo_leche", "precio": 5000},
        {"nombre": "Soda saborizada", "id": "soda_saborizada", "precio": 3500},
        {"nombre": "Milo", "id": "milo", "precio": 4500},
        {"nombre": "Aromática", "id": "aromatica", "precio": 2500},
        {"nombre": "Tinto", "id": "tinto", "precio": 1500},
        {"nombre": "Café con leche", "id": "cafe_leche", "precio": 3000},
    ],
    "Adiciones": [
        {"nombre": "Carne desmechada BBQ", "id": "carne_desmechada_bbq", "precio": 3000},
        {"nombre": "Carne desmechada Crioya", "id": "carne_desmechada_crioya", "precio": 3000},
        {"nombre": "Pollo desmechado", "id": "pollo_desmechado", "precio": 2500},
        {"nombre": "Chicharrón", "id": "chicharron", "precio": 2000},
        {"nombre": "Costillas BBQ", "id": "costillas_bbq", "precio": 4000},
        {"nombre": "Chorizo", "id": "chorizo", "precio": 2500},
        {"nombre": "Salchicha ranchera", "id": "salchicha_ranchera", "precio": 2000},
        {"nombre": "Queso mozzarella", "id": "queso_mozzarella", "precio": 1500},
        {"nombre": "Tocineta", "id": "tocineta", "precio": 2000},
        {"nombre": "Pico de gallo", "id": "pico_gallo", "precio": 1000},
        {"nombre": "Madurito", "id": "madurito", "precio": 1500},
        {"nombre": "Maíz tierno", "id": "maiz_tierno", "precio": 1500},
    ],
}

LOCATION_KEY = os.getenv("LOCATION_KEY")

def _build_products(menu: dict) -> dict:
    """Convierte el menú en el formato utilizado por el formulario."""
    productos = {}
    for categoria in menu.values():
        for item in categoria:
            productos[item["id"]] = {"label": item["nombre"], "sizes": ["base"]}
    return productos


# Lista sencilla de adiciones para el formulario
ADICIONES = [i["nombre"] for i in MENU_FORMULARIO.get("Adiciones", [])]


PRODUCTS = _build_products(MENU_FORMULARIO)

# Coordenadas y radio de cobertura
LOCAL_COORDS = (6.172720899383694, -75.33313859325239)  # Coordenadas del local
RADIO_COBERTURA = 50000  # 6 km de cobertura

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


def _crear_pedido_response(
    productos: List[str],
    cantidades: List[int],
    tamanos: List[str],
    adiciones: List[str],
    detalles: List[str],
    nombre_apellido: str,
    telefono: str,
    direccion: str,
    domicilio: bool,
) -> schemas.PedidoResponse:
    """Construye un objeto de respuesta de pedido a partir de los campos del formulario."""
    items: list[schemas.PedidoItem] = []
    for producto, cantidad, tamano, adicion, detalle in zip(
        productos, cantidades, tamanos, adiciones, detalles
    ):
        if cantidad <= 0:
            continue
        label = PRODUCTS.get(producto, {}).get("label", producto)
        items.append(
            schemas.PedidoItem(
                producto=label,
                cantidad=cantidad,
                tamano=tamano,
                adicion=adicion or None,
                detalle=detalle or None,
            )
        )

    return schemas.PedidoResponse(
        nombre=nombre_apellido,
        telefono=telefono,
        direccion=direccion,
        domicilio=domicilio,
        pedido=items,
    )

async def _procesar_pedido(
    request: Request,
    productos: List[str],
    cantidades: List[int],
    tamanos: List[str],
    adiciones: List[str],
    detalles: List[str],
    nombre_apellido: str,
    telefono: str,
    direccion: str,
    domicilio: bool,
):
    """Genera la respuesta con el resumen del pedido."""
    pedido = _crear_pedido_response(
        productos,
        cantidades,
        tamanos,
        adiciones,
        detalles,
        nombre_apellido,
        telefono,
        direccion,
        domicilio,
    )
    return templates.TemplateResponse(
        "pedido_resumen.html",
        {
            "request": request,
            "pedido": pedido.pedido,
            "nombre": pedido.nombre,
            "telefono": pedido.telefono,
            "direccion": pedido.direccion,
            "domicilio": pedido.domicilio,
        },
    )


@app.get("/atencion", response_class=HTMLResponse)
async def atencion(request: Request):
    return templates.TemplateResponse(
        "pedidos.html",
        {
            "request": request,
            "products": PRODUCTS,
            "adiciones": ADICIONES,
            "titulo": "Atenci\u00f3n al Cliente",
        },
    )


@app.post("/atencion", response_class=HTMLResponse)
async def submit_atencion(
    request: Request,
    telefono: str = Form(...),
    nombre_apellido: str = Form(...),
    direccion: str = Form(""),
    domicilio: bool = Form(False),
    productos: List[str] = Form(...),
    cantidades: List[int] = Form(...),
    tamanos: List[str] = Form(...),
    adiciones: List[str] = Form(...),
    detalles: List[str] = Form(...),
):
    return await _procesar_pedido(
        request,
        productos,
        cantidades,
        tamanos,
        adiciones,
        detalles,
        nombre_apellido,
        telefono,
        direccion if domicilio else "",
        domicilio,
    )

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


@app.post("/pedido", response_model=schemas.PedidoResponse)
async def crear_pedido(
    telefono: str = Form(...),
    nombre_apellido: str = Form(...),
    direccion: str = Form(""),
    domicilio: bool = Form(False),
    productos: List[str] = Form(...),
    cantidades: List[int] = Form(...),
    tamanos: List[str] = Form(...),
    adiciones: List[str] = Form(...),
    detalles: List[str] = Form(...),
):
    """Recibe los campos del formulario y devuelve un objeto de pedido."""
    return _crear_pedido_response(
        productos,
        cantidades,
        tamanos,
        adiciones,
        detalles,
        nombre_apellido,
        telefono,
        direccion if domicilio else "",
        domicilio,
    )

@app.post('/zona', response_model=schemas.ZonaResponse)
async def zona(direccion: str = Form(...)):
    geolocator = OpenCage(LOCATION_KEY, timeout=10, ssl_context=ctx)
    location = geolocator.geocode(direccion, exactly_one=True)
    if not location:
        return {"response": "bad", "mensaje": "Dirección no encontrada"}
    direccion_coords = (location.latitude, location.longitude)
    distancia = geodesic(LOCAL_COORDS, direccion_coords).meters
    if distancia <= RADIO_COBERTURA:
        return {"response": "ok", "mensaje": "En zona de cobertura"}
    else:
        return {"response": "bad", "mensaje": "Fuera de cobertura"}



#Parte Paulina Revisar 


@app.post("/cliente", response_model=schemas.ClienteRegistroResponse)
async def registrar_o_verificar_cliente(
    nombre_apellido: str = Form(...),
    direccion: str = Form(...),
    telefono: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validación: campos vacíos
    if not nombre_apellido.strip() or not direccion.strip() or not telefono.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faltan datos obligatorios para registrar al cliente"
        )

    # Verificar si ya existe
    cliente_existente = db.query(models.Cliente).filter(models.Cliente.telefono == telefono).first()

    if cliente_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya está registrado"
        )

    # Crear nuevo cliente
    nuevo_cliente = models.Cliente(
        nombre_apellido=nombre_apellido,
        direccion=direccion,
        telefono=telefono
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)

    return {
        "mensaje": "Cliente registrado exitosamente",
        "cliente": {
            "nombre": nuevo_cliente.nombre_apellido,
            "direccion": nuevo_cliente.direccion,
            "telefono": nuevo_cliente.telefono
        }
    }

@app.get("/cliente/{telefono}", response_model=schemas.ClienteBase)
async def obtener_cliente(telefono: str, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.telefono == telefono).first()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    return {
        "nombre": cliente.nombre_apellido,
        "direccion": cliente.direccion,
        "telefono": cliente.telefono
    }