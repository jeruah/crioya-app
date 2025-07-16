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
SESSION_SECRET=
STAFF_TOKEN=
```

Puede tomar como referencia el archivo `.env.example` incluido en el repositorio.

## Despliegue con Docker en Render

Para generar una imagen Docker ejecuta:

```bash
docker build -t crioya-app .
```

Luego puedes probarla localmente con:

```bash
docker run --env-file .env -p 8000:8000 crioya-app
```

En Render selecciona **New Web Service**, elige el entorno *Docker* y conecta el repositorio.
La plataforma construirá la imagen usando el `Dockerfile` y expondrá el servicio en el puerto 8000.

Ademas para el desplliegue en Render, debe cambiar la linea ws:// as wss:// en cocina.html

## Database indexes

Version 2 adds indexes to various timestamp columns (`facturas.fecha`, `cierres_caja.fecha`,
`entradas_insumo.fecha`, `salidas_insumo.fecha` y `movimientos.fecha`).
Si ya tienes las tablas creadas ejecuta manualmente `CREATE INDEX` para cada
columna o recrea las tablas para aprovechar los nuevos índices.

## Foreign key cascades

Versión 3 cambia las relaciones de `entradas_insumo` y `salidas_insumo` para
eliminar automáticamente los registros asociados cuando un `insumo` se borra.
Debes recrear las tablas para que los `FOREIGN KEY` tengan `ON DELETE CASCADE`.

Ejecuta:

```bash
python scripts/recreate_tables.py
```

Esto eliminará todas las tablas y las volverá a crear con las claves
actualizadas.
