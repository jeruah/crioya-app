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
