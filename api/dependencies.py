from typing import Generator, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from db.config import settings
from db.database import DatabaseManager

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]", "testclient", "testserver"}


def get_db_session(request: Request = None) -> Generator[Session, None, None]:
    """Provee una sesión de base de datos SQLAlchemy por solicitud HTTP, respetando X-Target-Environment en localhost."""
    env_target = None
    if request is not None and hasattr(request, "headers"):
        if is_localhost_request(request):
            env_target = request.headers.get("x-target-environment")

    db = DatabaseManager.get_instance_for_env(env_target)
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def is_localhost_request(request: Optional[Request]) -> bool:
    """Verifica de forma estricta que la petición provenga de localhost sin proxys externos."""
    if request is None or not hasattr(request, "headers"):
        return not settings.is_production

    if request.headers.get("x-vercel-id"):
        return False

    forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip().lower()
        if first_ip and first_ip not in _LOOPBACK_HOSTS:
            return False

    forwarded_host = (request.headers.get("x-forwarded-host") or "").strip().lower()
    if forwarded_host:
        clean_fhost = forwarded_host.split(":")[0].strip()
        if clean_fhost and clean_fhost not in _LOOPBACK_HOSTS:
            return False

    host_header = (request.headers.get("host") or "").strip().lower()
    if host_header:
        if host_header.startswith("["):
            clean_host = host_header.split("]")[0] + "]"
        else:
            clean_host = host_header.split(":")[0].strip()
        if clean_host and clean_host not in _LOOPBACK_HOSTS:
            return False

    origin_header = (request.headers.get("origin") or "").strip()
    if origin_header:
        try:
            from urllib.parse import urlparse
            parsed_origin = urlparse(origin_header)
            origin_host = (parsed_origin.hostname or "").strip().lower()
            if origin_host and origin_host not in _LOOPBACK_HOSTS:
                return False
        except Exception:
            return False

    client_host = (request.client.host if request.client else "127.0.0.1").strip().lower()
    if client_host not in _LOOPBACK_HOSTS:
        return False

    return True


def require_local_admin(request: Request) -> None:
    """Dependencia de seguridad: restringe endpoints administrativos exclusivamente a localhost."""
    if request.method == "OPTIONS":
        return
    if not settings.is_local_admin_enabled or not is_localhost_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: La administración de tiendas y catálogo está disponible únicamente en entorno local (localhost).",
        )


def require_local_analytics(request: Request) -> None:
    """Dependencia de seguridad: restringe analítica y reporte de sincronización exclusivamente a localhost."""
    if request.method == "OPTIONS":
        return
    if not settings.is_analytics_enabled or not is_localhost_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: El reporte de sincronización y analítica está disponible únicamente en entorno local (localhost).",
        )

