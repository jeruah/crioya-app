import os
import ssl
import certifi
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Any
from openai import AzureOpenAI

load_dotenv()

templates = Jinja2Templates(directory="templates")

def render_template(request: Request, name: str, context: dict[str, Any] | None = None):
    ctx = context or {}
    ctx["request"] = request
    ctx["error"] = request.session.pop("error", None)
    return templates.TemplateResponse(name, ctx)
ctx = ssl.create_default_context(cafile=certifi.where())
LOCATION_KEY = os.getenv("LOCATION_KEY")
AZURE_KEY = os.getenv("azure_key")
AZURE_ENDPOINT = os.getenv("azure_endpoint")
STAFF_TOKEN = os.getenv("STAFF_TOKEN", "changeme")

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


def _build_products(menu: dict) -> dict:
    """Convierte el menú en el formato utilizado por el formulario."""
    productos = {}
    for categoria in menu.values():
        for item in categoria:
            productos[item["id"]] = {"label": item["nombre"], "sizes": ["base"]}
    return productos

cliente_azure = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_KEY,
    api_version="2024-12-01-preview"
)

ADICIONES = [i["nombre"] for i in MENU_FORMULARIO.get("Adiciones", [])]
PRODUCTS = _build_products(MENU_FORMULARIO)

LOCAL_COORDS = (6.172720899383694, -75.33313859325239)
RADIO_COBERTURA = 2500
