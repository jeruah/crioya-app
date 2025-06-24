from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models, schemas, dependencies
from ..config import MENU_FORMULARIO  # 🛒 Importa el menú con precios
import json
from datetime import datetime, timedelta
import pandas as pd
import io
from fpdf import FPDF
import pytz
import time

router = APIRouter()

# 🔧 Construye un diccionario {nombre_producto: precio}
def construir_diccionario_precios(menu: dict) -> dict:
    precios = {}
    for categoria in menu.values():
        for item in categoria:
            precios[item["nombre"]] = item["precio"]
    return precios

# Diccionario global de precios
PRECIOS = construir_diccionario_precios(MENU_FORMULARIO)

# Cache simple para evitar consultas repetidas
CACHE_TTL = 300  # segundos
_factura_cache: dict[str, object] = {"df": None, "time": 0.0}

def _load_cache(db: Session) -> pd.DataFrame:
    """Devuelve un DataFrame con las facturas, usando cache en memoria."""
    now = time.time()
    if _factura_cache["df"] is None or now - _factura_cache["time"] > CACHE_TTL:
        facturas = db.query(models.Factura).all()
        data = [
            {
                "id": f.id,
                "numero": f.numero,
                "fecha": f.fecha,
                "cliente": f.cliente,
                "productos": f.productos,
                "total": f.total,
            }
            for f in facturas
        ]
        _factura_cache["df"] = pd.DataFrame(data)
        _factura_cache["time"] = now
    return _factura_cache["df"]

def generar_factura_desde_pedido(pedido: schemas.PedidoResponse, db: Session) -> models.Factura:
    colombia = pytz.timezone("America/Bogota")
    fecha_local = datetime.now(colombia)
    fecha_actual_str = fecha_local.strftime("%Y%m%d")

    productos_pedido = [item.dict() for item in pedido.pedido]
    total = 0
    productos_desglosados = []

    for item in productos_pedido:
        nombre = item.get("producto")
        cantidad = item.get("cantidad", 0)
        adiciones = item.get("adicion") or []

        precio_unitario = PRECIOS.get(nombre, 0)
        subtotal = cantidad * precio_unitario

        adiciones_detalle = []
        for adicion in adiciones:
            precio_adicion = PRECIOS.get(adicion, 0)
            subtotal += precio_adicion
            adiciones_detalle.append({"nombre": adicion, "precio": precio_adicion})

        productos_desglosados.append({
            "producto": nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "adiciones": adiciones_detalle,
            "subtotal": subtotal
        })

        total += subtotal

    conteo_hoy = db.query(models.Factura).filter(
        models.Factura.numero.like(f"FAC-{fecha_actual_str}-%")
    ).count() + 1
    numero_factura = f"FAC-{fecha_actual_str}-{conteo_hoy:03d}"

    factura = models.Factura(
        numero=numero_factura,
        fecha=fecha_local,
        cliente=pedido.nombre,
        productos=json.dumps(productos_desglosados),
        total=total
    )

    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


#  Esta función quedó obsoleta porque ya no usamos la base de datos de pedidos
'''@router.post("/factura/{pedido_id}", response_model=schemas.FacturaResponse)
def generar_factura(pedido_id: int, db: Session = Depends(dependencies.get_db)):
    # Buscar el pedido por ID
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Obtener hora actual en Colombia
    colombia = pytz.timezone("America/Bogota")
    fecha_local = datetime.now(colombia)
    print("📅 Fecha y hora local en Colombia:", fecha_local) 
    fecha_actual_str = fecha_local.strftime("%Y%m%d")

    # Procesar productos
    productos_pedido = json.loads(pedido.productos)
    total = 0
    productos_desglosados = []

    for item in productos_pedido:
        nombre = item.get("producto")
        cantidad = item.get("cantidad", 0)
        adiciones = item.get("adicion") or []

        precio_unitario = PRECIOS.get(nombre, 0)
        subtotal = cantidad * precio_unitario

        adiciones_detalle = []
        for adicion in adiciones:
            precio_adicion = PRECIOS.get(adicion, 0)
            subtotal += precio_adicion
            adiciones_detalle.append({"nombre": adicion, "precio": precio_adicion})

        productos_desglosados.append({
            "producto": nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "adiciones": adiciones_detalle,
            "subtotal": subtotal
        })

        total += subtotal

    # Número de factura
    conteo_hoy = db.query(models.Factura).filter(models.Factura.numero.like(f"FAC-{fecha_actual_str}-%")).count() + 1
    numero_factura = f"FAC-{fecha_actual_str}-{conteo_hoy:03d}"

    # Crear factura
    factura = models.Factura(
        numero=numero_factura,
        fecha=fecha_local,
        cliente=pedido.nombre_apellido,
        productos=json.dumps(productos_desglosados),
        total=total
    )

    db.add(factura)
    db.commit()
    db.refresh(factura)

    return factura'''


# API de facturas con filtrado por fechas
@router.get("/api/facturas", response_model=list[schemas.FacturaResponse])
def listar_facturas(
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(dependencies.get_db),
):
    df = _load_cache(db)
    filtered = df
    if start:
        filtered = filtered[filtered["fecha"] >= pd.to_datetime(start)]
    if end:
        fecha_limite = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[filtered["fecha"] <= fecha_limite]
    data = filtered.to_dict(orient="records")
    # Deserializar productos de JSON
    for row in data:
        if isinstance(row["productos"], str):
            row["productos"] = json.loads(row["productos"])
    return [schemas.FacturaResponse(**row) for row in data]


@router.get("/api/facturas/excel")
def exportar_excel(
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(dependencies.get_db),
):
    df = _load_cache(db)
    if start:
        df = df[df["fecha"] >= pd.to_datetime(start)]
    if end:
        fecha_limite = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df = df[df["fecha"] <= fecha_limite]
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=facturas.xlsx"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/api/facturas/{factura_id}/pdf")
def descargar_pdf(factura_id: int, db: Session = Depends(dependencies.get_db)):
    df = _load_cache(db)
    fila = df[df["id"] == factura_id]
    if fila.empty:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    factura = fila.iloc[0]
    productos = json.loads(factura["productos"])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Factura {factura['numero']}", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Fecha: {factura['fecha']}", ln=True)
    pdf.cell(0, 10, f"Cliente: {factura['cliente']}", ln=True)
    pdf.ln(5)
    for item in productos:
        detalle = f"{item.get('producto')} x{item.get('cantidad')} - {item.get('subtotal')}"
        pdf.cell(0, 10, detalle, ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Total: {factura['total']}", ln=True)
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    headers = {
        "Content-Disposition": f"attachment; filename=factura_{factura['numero']}.pdf"
    }
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)

