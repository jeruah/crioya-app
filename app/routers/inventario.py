from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from datetime import date
from sqlalchemy import cast, Date
from fastapi import Query
from datetime import date
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

INSUMOS_PREDEFINIDOS = [
    {"nombre": "Papas Criolla", "unidad": "kg", "minimo": 100},
    {"nombre": "Papa Normal", "unidad": "kg", "minimo": 100},
    {"nombre": "Deditos De Queso", "unidad": "kg", "minimo": 40},
    {"nombre": "Yucas", "unidad": "kg", "minimo": 50},
    {"nombre": "Salchicha Ranchera", "unidad": "kg", "minimo": 4},
    {"nombre": "Costillas", "unidad": "kg", "minimo": 40},
    {"nombre": "Pico De Gallo", "unidad": "kg", "minimo": 70},
    {"nombre": "Nachos", "unidad": "kg", "minimo": 50},
    {"nombre": "Queso", "unidad": "kg", "minimo": 25},
    {"nombre": "Chicharron", "unidad": "kg", "minimo": 40},
    {"nombre": "Carne Desmechada", "unidad": "kg", "minimo": 45},
    {"nombre": "Pan De Hamburguesa", "unidad": "kg", "minimo": 6},
    {"nombre": "Carne De Hamburguesa", "unidad": "kg", "minimo": 80},
    {"nombre": "Lechuga", "unidad": "kg", "minimo": 10},
    {"nombre": "Tomate", "unidad": "kg", "minimo": 20},
    {"nombre": "Tocineta", "unidad": "kg", "minimo": 20},
    {"nombre": "Pan De Perro", "unidad": "kg", "minimo": 20},
    {"nombre": "Salchicha Zenu", "unidad": "kg", "minimo": 50},
    {"nombre": "Nuggets", "unidad": "kg", "minimo": 60},
    {"nombre": "Platano", "unidad": "kg", "minimo": 15},
    {"nombre": "Suero Costeño", "unidad": "kg", "minimo": 4},
    {"nombre": "Pollo Desmechado", "unidad": "kg", "minimo": 5},
    {"nombre": "Maiz Tierno", "unidad": "kg", "minimo": 5},
    {"nombre": "Butifarra", "unidad": "kg", "minimo": 10},
    {"nombre": "Cebolla", "unidad": "kg", "minimo": 2},
    {"nombre": "Productos Postobon De 400ml", "unidad": "unidad", "minimo": 10},
    {"nombre": "Pulpa De Frutas", "unidad": "kg", "minimo": 5},
    {"nombre": "Sodas", "unidad": "kg", "minimo": 10},
    {"nombre": "Leche", "unidad": "kg", "minimo": 5},
    {"nombre": "Saborizantes", "unidad": "kg", "minimo": 2},
    {"nombre": "Hielo", "unidad": "kg", "minimo": 5},
    {"nombre": "Cocacola 300ml", "unidad": "unidad", "minimo": 10},
    {"nombre": "Productos Postobon 1.5 Litros", "unidad": "unidad", "minimo": 5},
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
def agregar(nombre: str = Form(...), unidad: str = Form(...), cantidad: float = Form(...), minimo: float = Form(...), db: Session = Depends(get_db)):
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
    fin = datetime.combine(fecha, datetime.max.time())     # 23:59:59.999999

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
