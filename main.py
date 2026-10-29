import os
from api.app_public import create_public_app

# Por defecto, main.py ejecuta la Parte 1: Sitio Público y Administración de Tiendas por Encargado
app = create_public_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"☕ Iniciando Servidor Público y Portal de Tiendas en http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
