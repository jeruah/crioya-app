# app/models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy import Boolean, Text
from .database import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_apellido = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    telefono = Column(String, unique=True, index=True, nullable=False)



# 📦 Modelo que representa un pedido completo en la base de datos
class Pedido(Base):
    __tablename__ = "pedidos"  # Nombre de la tabla en la base de datos

    id = Column(Integer, primary_key=True, index=True)  
    nombre_apellido = Column(String, nullable=False)    
    telefono = Column(String, nullable=False)           
    direccion = Column(String, nullable=True)           
    domicilio = Column(Boolean, default=False)          
    productos = Column(Text, nullable=False)            # Contiene el listado de productos como JSON serializado
