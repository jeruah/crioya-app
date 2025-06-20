from typing import List

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
)

router = APIRouter()

manager = schemas.ConnectionManager()


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


@router.post("/atencion")
async def submit_atencion(
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
    msg = await nuevo_pedido(pedido)
    print(msg)
    response = RedirectResponse(url="/resumen", status_code=303)
    response.set_cookie("ultimo_pedido", pedido.model_dump_json(), max_age=300)
    return response


@router.get("/resumen", response_class=HTMLResponse)
async def resumen_pedido(request: Request):
    pedido_json = request.cookies.get("ultimo_pedido")
    if not pedido_json:
        return RedirectResponse(url="/atencion")
    pedido = schemas.PedidoResponse.model_validate_json(pedido_json)
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
    geolocator = OpenCage(LOCATION_KEY, timeout=10, ssl_context=ctx)
    location = geolocator.geocode(direccion, exactly_one=True)
    if not location:
        return {"response": "bad", "mensaje": "Direcci\u00f3n no encontrada"}
    direccion_coords = (location.latitude, location.longitude)
    distancia = geodesic(LOCAL_COORDS, direccion_coords).meters
    if distancia <= RADIO_COBERTURA:
        return {"response": "ok", "mensaje": "En zona de cobertura"}
    else:
        return {"response": "bad", "mensaje": "Fuera de cobertura"}
