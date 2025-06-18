# app/models.py
from sqlalchemy import Column, Integer, String
from .database import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_apellido = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    telefono = Column(String, unique=True, index=True, nullable=False)

