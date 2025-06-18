from pydantic import BaseModel

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
    """Información de un producto dentro de un pedido."""

    producto: str
    cantidad: int
    tamano: str
    adicion: str | None = None
    detalle: str | None = None

    class Config:
        from_attributes = True


class PedidoResponse(BaseModel):
    """Representación completa del pedido recibido."""

    nombre: str
    telefono: str
    direccion: str
    domicilio: bool
    pedido: list[PedidoItem]

    class Config:
        from_attributes = True

