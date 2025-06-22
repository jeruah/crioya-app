# Crioya Sales App

Aplicaci\u00f3n b\u00e1sica de gesti\u00f3n de ventas para una empresa de papas criollas.

## Requisitos

- Python 3.8+
- Dependencias del archivo `requirements.txt`

## Uso

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar la aplicaci\u00f3n:

```bash
uvicorn app.main:app --reload
```

La aplicación utiliza cookies de sesión a través de `SessionMiddleware`. Puedes
definir la clave de sesión estableciendo la variable de entorno
`SESSION_SECRET`.

Abrir en el navegador `http://localhost:8000`.

La aplicación cuenta con un formulario para registrar pedidos que también se
utiliza en el módulo de atención al cliente.
Desde la interfaz de pedidos ahora es posible agregar múltiples adiciones a un
producto y eliminar tanto adiciones individuales como productos completos.

## Autenticacion de cocina

Para acceder al WebSocket de cocina se requiere un token. Establece la variable de entorno `STAFF_TOKEN` con un valor compartido y el navegador incluirá ese token al conectarse a `/ws/cocina`.

## Variables de entorno

Cree un archivo `.env` en la raíz del proyecto con las siguientes claves:

```
user=
password=
host=
port=
dbname=
LOCATION_KEY=
azure_key=
azure_endpoint=
```

Puede tomar como referencia el archivo `.env.example` incluido en el repositorio.
