# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy import Boolean, Text
from .database import Base
from datetime import datetime
import pytz

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_apellido = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    telefono = Column(String, unique=True, index=True, nullable=False)



# 📦 Modelo que representa un pedido completo en la base de datos
'''
class Pedido(Base):
    __tablename__ = "pedidos"  # Nombre de la tabla en la base de datos

    id = Column(Integer, primary_key=True, index=True)  
    nombre_apellido = Column(String, nullable=False)    
    telefono = Column(String, nullable=False)           
    direccion = Column(String, nullable=True)           
    domicilio = Column(Boolean, default=False)          
    productos = Column(Text, nullable=False)            # Contiene el listado de productos como JSON serializado
'''
# Factura en base de datos

def hora_colombia():
    return datetime.now(pytz.timezone("America/Bogota"))

class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, nullable=False)  # Ej: FAC-20250622-001
    fecha = Column(DateTime, default=hora_colombia)  
    cliente = Column(String, nullable=False)
    productos = Column(Text, nullable=False)  # JSON serializado con productos
    total = Column(Float, nullable=False)


# Modelo para el cierre de caja
class CierreCaja(Base):
    __tablename__ = "cierres_caja"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=hora_colombia)
    efectivo = Column(Float, nullable=False)
    digital = Column(Float, nullable=False)
    total_recibido = Column(Float, nullable=False)
    total_facturado = Column(Float, nullable=False)
    diferencia = Column(Float, nullable=False)
    observaciones = Column(Text, nullable=True)