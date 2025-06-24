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
    render_template,
    PRODUCTS,
    ADICIONES,
    LOCATION_KEY,
    ctx,
    LOCAL_COORDS,
    RADIO_COBERTURA,
    cliente_azure,
    STAFF_TOKEN,
)

from sqlalchemy.orm import Session
from fastapi import Depends
from .. import models, dependencies
from ..errors import AppError
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
    pedido_data = request.session.pop("pedido_data", None)
    return render_template(
        request,
        "pedidos.html",
        {
            "products": PRODUCTS,
            "adiciones": ADICIONES,
            "titulo": "Atenci\u00f3n al Cliente",
            "pedido_data": pedido_data,
        },
    )


async def nuevo_pedido(pedido: schemas.PedidoResponse):
    await manager.broadcast(pedido.model_dump_json())
    return {"mensaje": "Pedido enviado a la cocina"}


from sqlalchemy.orm import Session
from fastapi import Depends
from .. import models, dependencies
import json
from ..routers.facturas import generar_factura_desde_pedido


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

    try:
        factura = generar_factura_desde_pedido(pedido, db)
        await nuevo_pedido(pedido)
    except Exception as e:
        request.session["pedido_data"] = pedido.model_dump()
        raise AppError("No se pudo procesar el pedido") from e

    request.session["success"] = "Pedido enviado a cocina y factura generada"

  
    return render_template(
        request,
        "pedido_resumen.html",
        {
            "pedido": [item.dict() for item in pedido.pedido],
            "nombre": pedido.nombre,
            "telefono": pedido.telefono,
            "direccion": pedido.direccion,
            "domicilio": pedido.domicilio,
        },
    )


@router.get("/resumen", response_class=HTMLResponse)
async def resumen_pedido(request: Request, id: int, db: Session = Depends(dependencies.get_db)):
    factura = db.query(models.Factura).filter(models.Factura.id == id).first()
    if not factura:
        return RedirectResponse(url="/atencion")

    productos = json.loads(factura.productos)
    print("DEBUG productos:", productos)  # <-- Agrega esta línea aquí

    return render_template(
        request,
        "pedido_resumen.html",
        {
            "pedido": productos,
            "nombre": factura.cliente,
            "telefono": "",
            "direccion": "",
            "domicilio": False,
        },
    )



@router.websocket("/ws/cocina")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if token != STAFF_TOKEN:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/cocina", response_class=HTMLResponse)
async def cocina(request: Request):
    return render_template(request, "cocina.html", {"token": STAFF_TOKEN})


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
