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
from io import BytesIO

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
        df = pd.DataFrame(data)
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.tz_localize("UTC")  # 🔧 Fix aquí
        _factura_cache["df"] = df
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

    try:
        db.add(factura)
        db.commit()
        db.refresh(factura)
    except Exception as e:
        db.rollback()
        from ..errors import DatabaseError
        raise DatabaseError("Error registrando la factura") from e
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
'''@router.get("/api/facturas", response_model=list[schemas.FacturaResponse])
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
    return [schemas.FacturaResponse(**row) for row in data]'''
from_zone = pytz.timezone("America/Bogota")

@router.get("/api/facturas", response_model=list[schemas.FacturaResponse])
def listar_facturas(
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(dependencies.get_db),
):
    df = _load_cache(db)
    filtered = df
    if start:
        start_dt = from_zone.localize(datetime.strptime(start, "%Y-%m-%d"))
        start_utc = start_dt.astimezone(pytz.utc)
        filtered = filtered[filtered["fecha"] >= start_utc]
    if end:
        end_dt = from_zone.localize(datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1))
        end_utc = end_dt.astimezone(pytz.utc)
        filtered = filtered[filtered["fecha"] < end_utc]

    data = filtered.to_dict(orient="records")
    for row in data:
        if isinstance(row["productos"], str):
            row["productos"] = json.loads(row["productos"])
    return [schemas.FacturaResponse(**row) for row in data]

'''@router.get("/api/facturas/excel")
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
    )'''
@router.get("/api/facturas/excel")
def exportar_excel(
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(dependencies.get_db),
):
    df = _load_cache(db)

    # Convertir fechas de filtro a UTC
    if start:
        start_dt = from_zone.localize(datetime.strptime(start, "%Y-%m-%d"))
        start_utc = start_dt.astimezone(pytz.utc)
        df = df[df["fecha"] >= start_utc]
    if end:
        end_dt = from_zone.localize(datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1))
        end_utc = end_dt.astimezone(pytz.utc)
        df = df[df["fecha"] < end_utc]

    # Convertir columna 'fecha' a hora local (Bogotá) y formato amigable
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], utc=True)
        df["fecha"] = df["fecha"].dt.tz_convert("America/Bogota")
        df["fecha"] = df["fecha"].dt.tz_localize(None)  # Necesario para Excel
        df["fecha"] = df["fecha"].dt.strftime("%d/%m/%Y %I:%M:%S %p")

    # Exportar a Excel
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

    # Convertir fecha a zona Bogotá
    from_zone = pytz.timezone("America/Bogota")
    fecha_valor = factura["fecha"]
    if isinstance(fecha_valor, datetime):
        fecha_local = fecha_valor.astimezone(from_zone)
    else:
        try:
            fecha_local = pd.to_datetime(fecha_valor, utc=True).tz_convert(from_zone)
        except Exception:
            fecha_local = datetime.now(from_zone)

    # Clase personalizada FPDF
    class PDF(FPDF):
        def multi_line(self, text, max_len):
            words = text.split(', ')
            lines, current = [], ''
            for word in words:
                if len(current + ', ' + word) < max_len:
                    current += (', ' if current else '') + word
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines

        def cell_fixed(self, w, h, txt, border=1, align='L'):
            self.multi_cell(w, h, txt, border=border, align=align)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()

    # Cabecera
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(255, 0, 0)
    pdf.cell(0, 10, f"Factura #{factura['numero']}", ln=True, align="C")
    pdf.ln(5)

    # Cliente y Fecha
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Cliente: {factura['cliente']}", ln=True)
    pdf.cell(0, 10, f"Fecha: {fecha_local.strftime('%d/%m/%Y %I:%M:%S %p')}", ln=True)
    pdf.ln(10)

    # Tabla: Encabezados
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(211, 211, 211)
    pdf.cell(50, 10, "Producto", border=1, align='C', fill=True)
    pdf.cell(20, 10, "Cantidad", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Precio Unit.", border=1, align='C', fill=True)
    pdf.cell(60, 10, "Adiciones", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Subtotal", border=1, align='C', fill=True)
    pdf.ln()

    # Tabla: Cuerpo
    pdf.set_font("Arial", size=11)
    for item in productos:
        producto = item.get('producto', '')
        cantidad = str(item.get('cantidad', ''))
        precio = f"${item.get('precio_unitario', 0):,.0f}"
        subtotal = f"${item.get('subtotal', 0):,.0f}"
        adiciones = ', '.join(a.get('nombre', '') for a in item.get('adiciones', []))

        # Dividir adiciones en líneas si es muy largo
        max_width = 55  # ancho en mm que cabe en la columna de adiciones
        pdf.set_font("Arial", size=11)
        adiciones_lines = pdf.multi_cell(60, 6, adiciones, border=0, align='L', split_only=True)
        line_count = len(adiciones_lines)
        row_height = max(10, 6 * line_count)

        x_start = pdf.get_x()
        y_start = pdf.get_y()

        # Producto
        pdf.set_xy(x_start, y_start)
        pdf.multi_cell(50, row_height, producto, border=1)

        # Cantidad
        pdf.set_xy(x_start + 50, y_start)
        pdf.cell(20, row_height, cantidad, border=1, align='C')

        # Precio unitario
        pdf.set_xy(x_start + 70, y_start)
        pdf.cell(30, row_height, precio, border=1, align='C')

        # Adiciones (multi-line)
        pdf.set_xy(x_start + 100, y_start)
        pdf.multi_cell(60, 6, adiciones, border=1, align='L')

        # Subtotal
        pdf.set_xy(x_start + 160, y_start)
        pdf.cell(30, row_height, subtotal, border=1, align='C')

        pdf.ln(row_height if row_height > 10 else 10)

    # Total
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Total: ${factura['total']:,.1f}", ln=True, align='R')

    # Salida
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    pdf_file = BytesIO(pdf_bytes)
    headers = {
        "Content-Disposition": f"attachment; filename=factura_{factura['numero']}.pdf",
        "Content-Type": "application/pdf"
    }
    return StreamingResponse(pdf_file, media_type="application/pdf", headers=headers)