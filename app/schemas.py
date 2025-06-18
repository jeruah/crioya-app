from pydantic import BaseModel

class ClienteBase(BaseModel):
    nombre: str
    direccion: str
    telefono: str

    class Config:
        orm_mode = True

class ClienteRegistroResponse(BaseModel):
    mensaje: str
    cliente: ClienteBase

class ZonaResponse(BaseModel):
    response: str
    mensaje: str
