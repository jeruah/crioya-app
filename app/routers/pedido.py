from typing import List
#from openai import AzureOpenAI

from fastapi import (
    APIRouter,
    Request,
    Form,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from geopy.geocoders import OpenCage
from geopy.distance import geodesic

from .. import schemas
from ..config import (
    templates,
    PRODUCTS,
    ADICIONES,
    LOCATION_KEY,
    ctx,
    LOCAL_COORDS,
    RADIO_COBERTURA,
    cliente_azure,
)

from sqlalchemy.orm import Session
from fastapi import Depends
from .. import models, dependencies
import json

router = APIRouter()

manager = schemas.ConnectionManager()

""" 
    solo quitar comentrarios si eres jeronimo, no lo toquen que me cobran plata
    def _formatear_direccion(direccion: str, cliente: AzureOpenAI) -> str:
        response = cliente.chat.completions.create(
            model="gpt-35-turbo-2",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Formatea la siguiente dirección colombiana para geocodificación, "
                        "reemplazando abreviaturas (CR, Cra, CL, Av, etc.),"
                        "en el caso de no estar abreviada, o no estar seguro de la abreviatura, dejarlo como está, "
                        "la letra que acompaña al primer numero ejemplo '10 b' o '10b', no debe tener nigun espacio y debe estar pegado al numero, "
                        " usando el formato '#num1-num2' para números, "
                        "un formato de ejemplo sería 'Calle 10b #5-20 Medellin Antioquia', no conviertas numero a texto, "
                        "y asegura que termine tu respuesta finalize con 'Marinilla Antioquia':\n"
                        f"{direccion}"
                    ),
                }
            ],
            max_tokens=20,
        )
        return response.choices[0].message.content.strip()
"""

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
        adiciones_list = [a.strip() for a in adicion.split(",") if a.strip()]

        items.append(
            schemas.PedidoItem(
                producto=label,
                cantidad=cantidad,
                tamano=tamano,
                adicion=adiciones_list or None,
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


@router.get("/atencion", response_class=HTMLResponse)
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


async def nuevo_pedido(pedido: schemas.PedidoResponse):
    await manager.broadcast(pedido.model_dump_json())
    return {"mensaje": "Pedido enviado a la cocina"}


from sqlalchemy.orm import Session
from fastapi import Depends
from .. import models, dependencies
import json

@router.post("/atencion")
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
    db: Session = Depends(dependencies.get_db),  # ← conexión a la base de datos
):
    # Construir objeto del pedido desde los campos del formulario
    pedido = _crear_pedido_response(
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

    # Convertir la lista de productos en texto JSON
    productos_serializados = json.dumps([item.dict() for item in pedido.pedido])

    # Crear un nuevo registro del modelo Pedido
    nuevo_pedido = models.Pedido(
        nombre_apellido=nombre_apellido,
        telefono=telefono,
        direccion=direccion,
        domicilio=domicilio,
        productos=productos_serializados,
    )

    # Guardar en la base de datos
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)

    # Redirigir al resumen del pedido, pasando el ID por URL
    response = RedirectResponse(url=f"/resumen?id={nuevo_pedido.id}", status_code=303)
    return response



@router.get("/resumen", response_class=HTMLResponse)
async def resumen_pedido(request: Request, id: int, db: Session = Depends(dependencies.get_db)):
    # Buscar el pedido por ID en la base de datos
    pedido = db.query(models.Pedido).filter(models.Pedido.id == id).first()
    if not pedido:
        return RedirectResponse(url="/atencion")

    # Convertir el campo productos (JSON string) a lista de diccionarios
    productos = json.loads(pedido.productos)

    return templates.TemplateResponse(
        "pedido_resumen.html",
        {
            "request": request,
            "pedido": productos,
            "nombre": pedido.nombre_apellido,
            "telefono": pedido.telefono,
            "direccion": pedido.direccion,
            "domicilio": pedido.domicilio,
        },
    )



@router.websocket("/ws/cocina")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/cocina", response_class=HTMLResponse)
async def cocina(request: Request):
    return templates.TemplateResponse("cocina.html", {"request": request})


@router.post("/pedido", response_model=schemas.PedidoResponse)
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


@router.post("/zona", response_model=schemas.ZonaResponse)
async def zona(direccion: str = Form(...)):
    if not "marinilla" in direccion.lower():
        return {"response": "bad", "mensaje": "La direcci\u00f3n debe ser en Marinilla"}

    # direccion = _formatear_direccion(direccion, cliente_azure)
    # print(f"Direcci\u00f3n formateada: {direccion}")

    geolocator = OpenCage(LOCATION_KEY, timeout=10, ssl_context=ctx)
    location = geolocator.geocode(direccion, exactly_one=True)
    if not location:
        return {"response": "bad", "mensaje": "Direcci\u00f3n no encontrada"}

    confianza = location.raw.get("confidence", 0)
    print(f"Confianza de la direcci\u00f3n: {confianza}")

    direccion_coords = (location.latitude, location.longitude)
    if confianza < 9:
        return {"response": "bad", "mensaje": "Revisa que la direccion sea correcta"}
    distancia = geodesic(LOCAL_COORDS, direccion_coords).meters
    if distancia <= RADIO_COBERTURA:
        return {"response": "ok", "mensaje": "En zona de cobertura"}
    else:
        return {"response": "bad", "mensaje": "Fuera de cobertura"}
