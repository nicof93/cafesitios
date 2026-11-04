import os
from api.app_plataforma import create_plataforma_app

app = create_plataforma_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PLATAFORMA_BACKEND_PORT", "8001"))
    host = os.getenv("PLATAFORMA_BACKEND_HOST", "127.0.0.1")
    print(f"🚀 Iniciando Servidor de Plataforma de Administración (Superadmin) en http://{host}:{port}")
    uvicorn.run("plataforma_backend:app", host=host, port=port, reload=True)

