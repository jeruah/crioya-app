from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app import models
from datetime import date, timedelta
from sqlalchemy import cast, Date
from fastapi import Query
from datetime import date
from datetime import datetime
import pytz
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")
# h

INSUMOS_PREDEFINIDOS = [
    {"nombre": "Papas Criolla", "unidad": "kg", "minimo": 100, "precio_unitario": 4800},
    {"nombre": "Papa Normal", "unidad": "kg", "minimo": 100, "precio_unitario": 1915},
    {"nombre": "Deditos De Queso", "unidad": "kg", "minimo": 40, "precio_unitario": 20000},
    {"nombre": "Yucas", "unidad": "kg", "minimo": 50, "precio_unitario": 1970},
    {"nombre": "Salchicha Ranchera", "unidad": "kg", "minimo": 4, "precio_unitario": 8000},
    {"nombre": "Costillas", "unidad": "kg", "minimo": 40, "precio_unitario": 18000},
    {"nombre": "Pico De Gallo", "unidad": "kg", "minimo": 70, "precio_unitario": 4000},
    {"nombre": "Nachos", "unidad": "kg", "minimo": 50, "precio_unitario": 10000},
    {"nombre": "Queso", "unidad": "kg", "minimo": 25, "precio_unitario": 23200},
    {"nombre": "Chicharron", "unidad": "kg", "minimo": 40, "precio_unitario": 22000},
    {"nombre": "Carne Desmechada", "unidad": "kg", "minimo": 45, "precio_unitario": 25000},
    {"nombre": "Pan De Hamburguesa", "unidad": "kg", "minimo": 6, "precio_unitario": 5000},
    {"nombre": "Carne De Hamburguesa", "unidad": "kg", "minimo": 80, "precio_unitario": 1915},
    {"nombre": "Lechuga", "unidad": "kg", "minimo": 10, "precio_unitario": 1590},
    {"nombre": "Tomate", "unidad": "kg", "minimo": 20, "precio_unitario": 5100},
    {"nombre": "Tocineta", "unidad": "kg", "minimo": 20, "precio_unitario": 18000},
    {"nombre": "Pan De Perro", "unidad": "kg", "minimo": 20, "precio_unitario": 5000},
    {"nombre": "Salchicha Zenu", "unidad": "kg", "minimo": 50, "precio_unitario": 8000},
    {"nombre": "Nuggets", "unidad": "kg", "minimo": 60, "precio_unitario": 12000},
    {"nombre": "Platano", "unidad": "kg", "minimo": 15, "precio_unitario": 1740},
    {"nombre": "Suero Costeño", "unidad": "kg", "minimo": 4, "precio_unitario": 18000},
    {"nombre": "Pollo Desmechado", "unidad": "kg", "minimo": 5, "precio_unitario": 10000},
    {"nombre": "Maiz Tierno", "unidad": "kg", "minimo": 5, "precio_unitario": 2500},
    {"nombre": "Butifarra", "unidad": "kg", "minimo": 10, "precio_unitario": 12000},
    {"nombre": "Cebolla", "unidad": "kg", "minimo": 2, "precio_unitario": 2505},
    {"nombre": "Productos Postobon De 400ml", "unidad": "unidad", "minimo": 10, "precio_unitario": 800},
    {"nombre": "Pulpa De Frutas", "unidad": "kg", "minimo": 5, "precio_unitario": 8000},
    {"nombre": "Sodas", "unidad": "kg", "minimo": 10, "precio_unitario": 800},  # se asume unidad
    {"nombre": "Leche", "unidad": "kg", "minimo": 5, "precio_unitario": 2000},
    {"nombre": "Saborizantes", "unidad": "kg", "minimo": 2, "precio_unitario": 15000},
    {"nombre": "Hielo", "unidad": "kg", "minimo": 5, "precio_unitario": 1000},
    {"nombre": "Cocacola 300ml", "unidad": "unidad", "minimo": 10, "precio_unitario": 800},
    {"nombre": "Productos Postobon 1.5 Litros", "unidad": "unidad", "minimo": 5, "precio_unitario": 800},
]


@router.get("/inventario")
def ver_inventario(request: Request, db: Session = Depends(get_db)):
    try:
        print("🔍 Ruta /inventario llamada")
        insumos_db = db.query(models.Insumo).all()
        datos = []
        for ins in insumos_db:
            entradas = sum(e.cantidad for e in ins.entradas)
            salidas = sum(s.cantidad for s in ins.salidas)
            disponible = entradas - salidas
            alerta = disponible < ins.minimo
            datos.append({
                "id": ins.id,
                "nombre": ins.nombre,
                "unidad": ins.unidad,
                "minimo": ins.minimo,
                "disponible": disponible,
                "alerta": alerta
            })
        return templates.TemplateResponse("inventario.html", {
            "request": request,
            "insumos": datos,
            "predefinidos": INSUMOS_PREDEFINIDOS,
            "fecha_actual": date.today().isoformat()
        })
    except Exception as e:
        print("💥 ERROR:", e)
        raise e


@router.post("/inventario/agregar")
def agregar(nombre: str = Form(...), unidad: str = Form(...), cantidad: float = Form(...), minimo: float = Form(...),
            db: Session = Depends(get_db)):
    nuevo = models.Insumo(nombre=nombre, unidad=unidad, minimo=minimo)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    entrada = models.EntradaInsumo(insumo_id=nuevo.id, cantidad=cantidad)
    db.add(entrada)

    # ✅ Registrar en historial
    mov = models.MovimientoInsumo(insumo_id=nuevo.id, tipo="agregado", cantidad=cantidad)
    db.add(mov)

    db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/entrada")
def entrada(nombre: str = Form(...), cantidad: float = Form(...), db: Session = Depends(get_db)):
    insumo = db.query(models.Insumo).filter_by(nombre=nombre).first()

    if not insumo:
        insumo_info = next((i for i in INSUMOS_PREDEFINIDOS if i["nombre"] == nombre), None)
        if not insumo_info:
            raise HTTPException(status_code=404, detail="Insumo no encontrado ni en base ni en predefinidos")

        insumo = models.Insumo(
            nombre=insumo_info["nombre"],
            unidad=insumo_info["unidad"],
            minimo=insumo_info["minimo"]
        )
        db.add(insumo)
        db.commit()
        db.refresh(insumo)

    nueva = models.EntradaInsumo(insumo_id=insumo.id, cantidad=cantidad)
    db.add(nueva)

    # ✅ Registrar en historial
    mov = models.MovimientoInsumo(insumo_id=insumo.id, tipo="entrada", cantidad=cantidad)
    db.add(mov)
    print("✅ Movimiento guardado:", mov)

    db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/editar/{insumo_id}")
def editar(insumo_id: int, cantidad: float = Form(...), db: Session = Depends(get_db)):
    db.query(models.EntradaInsumo).filter_by(insumo_id=insumo_id).delete()
    db.query(models.SalidaInsumo).filter_by(insumo_id=insumo_id).delete()

    entrada = models.EntradaInsumo(insumo_id=insumo_id, cantidad=cantidad)
    db.add(entrada)

    # ✅ Registrar en historial
    mov = models.MovimientoInsumo(insumo_id=insumo_id, tipo="edicion", cantidad=cantidad)
    db.add(mov)

    db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/eliminar/{insumo_id}")
def eliminar(insumo_id: int, db: Session = Depends(get_db)):
    # ✅ Registrar en historial antes de eliminar
    mov = models.MovimientoInsumo(insumo_id=insumo_id, tipo="eliminacion")
    db.add(mov)

    db.query(models.Insumo).filter_by(id=insumo_id).delete()
    db.commit()
    return RedirectResponse("/inventario", status_code=303)


from sqlalchemy import and_, func


@router.get("/historial")
def ver_historial(request: Request, fecha: date = Query(...), db: Session = Depends(get_db)):
    inicio = datetime.combine(fecha, datetime.min.time())  # 00:00:00
    fin = datetime.combine(fecha, datetime.max.time())  # 23:59:59.999999

    movimientos = db.query(models.MovimientoInsumo).filter(
        and_(
            models.MovimientoInsumo.fecha >= inicio,
            models.MovimientoInsumo.fecha <= fin
        )
    ).all()

    return templates.TemplateResponse("historial.html", {
        "request": request,
        "fecha": fecha,
        "movimientos": movimientos
    })


from_zone = pytz.timezone("America/Bogota")  # Cambia por tu zona si es necesario

def ensure_aware(dt, zone):
    if dt.tzinfo is None:
        return zone.localize(dt)
    return dt

def get_precio_unitario(insumo_nombre: str):
    for ins in INSUMOS_PREDEFINIDOS:
        if ins["nombre"].lower() == insumo_nombre.lower():
            return ins["precio_unitario"]
    return 0  # Si no está en la lista, considera precio 0

@router.get("/inventario/estimado_gasto", tags=["inventario"])
def estimado_gasto_insumos(
        request: Request,
        db: Session = Depends(get_db),
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
):
    """
    Retorna el gasto estimado de insumos (salidas) en el rango de fechas dado.
    Si no se pasan fechas, calcula desde el inicio de la semana hasta ahora.
    """
    now = datetime.now(from_zone)
    if desde:
        dt = datetime.strptime(desde, "%Y-%m-%d")
        desde = ensure_aware(dt, from_zone).astimezone(pytz.utc)
    else:
        # calcular inicio de semana (lunes)
        dt = now - timedelta(days=now.weekday())
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        desde = ensure_aware(dt, from_zone).astimezone(pytz.utc)

    if hasta:
        dt = datetime.strptime(hasta, "%Y-%m-%d") + timedelta(days=1)
        hasta = ensure_aware(dt, from_zone).astimezone(pytz.utc)
    else:
        hasta = now.astimezone(pytz.utc)

    movimientos = (
        db.query(models.SalidaInsumo)
        .filter(
            models.SalidaInsumo.fecha >= desde,
            models.SalidaInsumo.fecha <= hasta
        )
        .all()
    )

    # Sumar cantidades y calcular gasto total por insumo
    resumen_cantidades = {}
    resumen_gasto = {}

    total_general_gastado = 0

    for mov in movimientos:
        insumo_nombre = mov.insumo.nombre
        cantidad = mov.cantidad or 0
        precio_unitario = get_precio_unitario(insumo_nombre)
        gasto = cantidad * precio_unitario

        # Suma cantidades por insumo
        resumen_cantidades[insumo_nombre] = resumen_cantidades.get(insumo_nombre, 0) + cantidad
        # Suma gasto por insumo
        resumen_gasto[insumo_nombre] = resumen_gasto.get(insumo_nombre, 0) + gasto


        total_general_gastado += gasto

    return templates.TemplateResponse("estimado_gasto.html", {
        "request": request,
        "desde": desde.astimezone(from_zone),
        "hasta": hasta.astimezone(from_zone),
        "detalle_por_insumo": resumen_cantidades,
        "gasto_por_insumo": resumen_gasto,
        "total_general": total_general_gastado
    })

