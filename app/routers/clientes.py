from fastapi import APIRouter, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_db

router = APIRouter()


@router.post("/cliente", response_model=schemas.ClienteRegistroResponse)
async def registrar_o_verificar_cliente(
    nombre_apellido: str = Form(...),
    direccion: str = Form(...),
    telefono: str = Form(...),
    db: Session = Depends(get_db),
):
    if not nombre_apellido.strip() or not direccion.strip() or not telefono.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faltan datos obligatorios para registrar al cliente",
        )

    cliente_existente = (
        db.query(models.Cliente).filter(models.Cliente.telefono == telefono).first()
    )

    if cliente_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya est\u00e1 registrado",
        )

    nuevo_cliente = models.Cliente(
        nombre_apellido=nombre_apellido,
        direccion=direccion,
        telefono=telefono,
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)

    return {
        "mensaje": "Cliente registrado exitosamente",
        "cliente": {
            "nombre": nuevo_cliente.nombre_apellido,
            "direccion": nuevo_cliente.direccion,
            "telefono": nuevo_cliente.telefono,
        },
    }


@router.get("/cliente/{telefono}", response_model=schemas.ClienteBase)
async def obtener_cliente(telefono: str, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.telefono == telefono).first()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return {
        "nombre": cliente.nombre_apellido,
        "direccion": cliente.direccion,
        "telefono": cliente.telefono,
    }
