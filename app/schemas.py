from pydantic import BaseModel
from fastapi  import WebSocket
from typing import List

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
        for connection in self.active_connections:
            await connection.send_text(message)