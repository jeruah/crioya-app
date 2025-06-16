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

Abrir en el navegador `http://localhost:8000`.

La aplicación cuenta con un formulario para registrar pedidos que también se
utiliza en el módulo de atención al cliente.
Desde la interfaz de pedidos ahora es posible agregar múltiples adiciones a un
producto y eliminar tanto adiciones individuales como productos completos.
