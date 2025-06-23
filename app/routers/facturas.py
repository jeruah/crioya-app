from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, dependencies
from ..config import MENU_FORMULARIO  # 🛒 Importa el menú con precios
import json
from datetime import datetime
import pytz

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


# Devolver los datos de la base de datos de factura en json
@router.get("/facturas", response_model=list[schemas.FacturaResponse])
def listar_facturas(db: Session = Depends(dependencies.get_db)):
    return db.query(models.Factura).all()

