from pydantic import BaseModel
from fastapi  import WebSocket
from typing import List
from datetime import datetime

class ClienteBase(BaseModel):
    nombre: str
    direccion: str
    telefono: str

    class Config:
        from_attributes = True

class ClienteRegistroResponse(BaseModel):
    mensaje: str
    cliente: ClienteBase

class ZonaResponse(BaseModel):
    response: str
    mensaje: str


class PedidoItem(BaseModel):
    producto: str
    cantidad: int
    tamano: str
    adicion: list[str] | None = None
    detalle: str | None = None


class PedidoResponse(BaseModel):
    """Representación completa del pedido recibido."""
    nombre: str
    telefono: str
    direccion: str
    domicilio: bool
    pedido: list[PedidoItem]

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)


# 🧾 Esquema que define cómo se verá un pedido cuando se devuelva desde la base de datos
class PedidoDB(BaseModel):
    
    id: int                                 
    nombre_apellido: str                    
    telefono: str                           
    direccion: str                          
    domicilio: bool                         
    productos: str                          
    

    class Config:
        from_attributes = True              # Permite convertir automáticamente desde objetos ORM de SQLAlchemy

# Definición del esquema de la factura
class FacturaCreate(BaseModel):
    cliente: str
    productos: list[PedidoItem]  
    total: float

class FacturaResponse(BaseModel):
    id: int
    numero: str
    fecha: datetime
    cliente: str
    productos: list[dict]
    total: float

    class Config:
        from_attributes = True



#Paulina
class InsumoBase(BaseModel):
    nombre: str
    cantidad_minima: float
    unidad_medida: str
    # No incluimos cantidad_actual aquí porque se gestiona con movimientos
    # Y tampoco 'activo', que es para la DB

class InsumoCreate(InsumoBase):
    # Hereda de InsumoBase. Podrías añadir campos específicos para la creación si los hubiera.
    pass

class InsumoUpdate(InsumoBase):
    # Para actualizaciones, todos los campos son opcionales
    nombre: str | None = None
    cantidad_minima: float | None = None
    unidad_medida: str | None = None
    activo: bool | None = None

class InsumoResponse(InsumoBase):
    id: int
    cantidad_actual: float
    activo: bool

    class Config:
        from_attributes = True

class MovimientoInventarioCreate(BaseModel):
    insumo_id: int
    tipo_movimiento: str # "entrada" o "salida"
    cantidad: float
    descripcion: str | None = None

class MovimientoInventarioResponse(BaseModel):
    id: int
    insumo_id: int
    tipo_movimiento: str
    cantidad: float
    fecha: datetime
    descripcion: str | None = None

    class Config:
        from_attributes = True