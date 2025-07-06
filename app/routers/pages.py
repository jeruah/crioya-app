from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..config import templates, render_template
from fastapi import Form, Depends
from sqlalchemy.orm import Session
from .. import dependencies
#from fastapi import Flash  # si no usas flash messages, omite esta línea
from fastapi.responses import RedirectResponse
from datetime import datetime, date, timedelta
import pytz
import json
from sqlalchemy import func
from .. import models
from fastapi.responses import JSONResponse
from fastapi import Query

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    print("🟢 Entró a /")
    return render_template(request, "index.html")


@router.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return render_template(request, "main.html")


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    """Vista para revisar facturas guardadas."""
    return render_template(
        request,
        "facturas.html",
        {"titulo": "Revisar Facturas"},
    )


@router.get("/informe", response_class=HTMLResponse)
async def informe(request: Request):
    return render_template(
        request,
        "placeholder.html",
        {"titulo": "Informe Financiero"},
    )

@router.get("/cierre", response_class=HTMLResponse)
async def cierre_caja_form(request: Request):
    return render_template(request, "cierre.html")


@router.post("/cierre", response_class=HTMLResponse)
async def cierre_preview(
    request: Request,
    efectivo: float = Form(...),
    digital: float = Form(...),
    db: Session = Depends(dependencies.get_db),
):
    # Obtener fecha actual en zona horaria Colombia
    colombia = pytz.timezone("America/Bogota")
    ahora = datetime.now(colombia)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    # Consultar todas las facturas de hoy
    facturas_hoy = db.query(models.Factura).filter(models.Factura.fecha >= inicio_dia).all()
    total_facturado = sum(f.total for f in facturas_hoy)
    num_facturas = len(facturas_hoy)

    total_recibido = efectivo + digital
    diferencia = total_recibido - total_facturado

    # Generar observación
    if diferencia == 0:
        observacion = "Cierre exacto"
    elif diferencia > 0:
        observacion = f"Sobrante de {diferencia:.2f}"
    else:
        observacion = f"Faltante de {abs(diferencia):.2f}"

    # Mostrar resumen antes de guardar
    return render_template(
        request,
        "cierre_resumen.html",
        {
            "efectivo": efectivo,
            "digital": digital,
            "total_facturado": total_facturado,
            "total_recibido": total_recibido,
            "diferencia": diferencia,
            "observacion": observacion,
            "num_facturas": num_facturas,
        },
    )

@router.post("/cierre/confirmar", response_class=HTMLResponse)
async def confirmar_cierre(
    request: Request,
    efectivo: float = Form(...),
    digital: float = Form(...),
    total_facturado: float = Form(...),
    total_recibido: float = Form(...),
    diferencia: float = Form(...),
    observacion: str = Form(...),
    db: Session = Depends(dependencies.get_db),
):
    colombia = pytz.timezone("America/Bogota")
    ahora = datetime.now(colombia)

    cierre = models.CierreCaja(
        fecha=ahora,
        efectivo=efectivo,
        digital=digital,
        total_recibido=total_recibido,
        total_facturado=total_facturado,
        diferencia=diferencia,
        observaciones=observacion
    )
    db.add(cierre)
    db.commit()

    request.session["success"] = "✅ Cierre de caja registrado exitosamente"
    return RedirectResponse("/cierre", status_code=303)

@router.get("/cierres", response_class=HTMLResponse)
async def ver_cierres(
    request: Request,
    db: Session = Depends(dependencies.get_db),
    start: str = None,
    end: str = None
):
    hoy = date.today()
    fecha_inicio = datetime.strptime(start, "%Y-%m-%d").date() if start else hoy
    fecha_fin = datetime.strptime(end, "%Y-%m-%d").date() if end else hoy

    inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(tzinfo=pytz.timezone("America/Bogota"))
    fin_dt = datetime.combine(fecha_fin + timedelta(days=1), datetime.min.time()).replace(tzinfo=pytz.timezone("America/Bogota"))

    cierres = (
        db.query(models.CierreCaja)
        .filter(models.CierreCaja.fecha >= inicio_dt, models.CierreCaja.fecha < fin_dt)
        .order_by(models.CierreCaja.fecha.desc())
        .all()
    )

    return render_template(
        request,
        "cierres_historico.html",
        {
            "cierres": cierres,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
        },
    )

@router.get("/api/cierres")
async def api_cierres(
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(dependencies.get_db)
):
    try:
        fecha_inicio = datetime.strptime(start, "%Y-%m-%d")
        fecha_fin = datetime.strptime(end, "%Y-%m-%d")
        fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)

        cierres = db.query(models.CierreCaja).filter(
            models.CierreCaja.fecha >= fecha_inicio,
            models.CierreCaja.fecha <= fecha_fin,
        ).all()

        resultados = [
            {
                "fecha": cierre.fecha.isoformat(),
                "efectivo": cierre.efectivo,
                "digital": cierre.digital,
                "total_recibido": cierre.total_recibido,
                "total_facturado": cierre.total_facturado,
                "diferencia": cierre.diferencia,
                "observaciones": cierre.observaciones,
            }
            for cierre in cierres
        ]

        return JSONResponse(content=resultados)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})