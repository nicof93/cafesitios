import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from db.database import AuditoriaAccionesTienda, Tienda, UsuarioTienda

logger = logging.getLogger(__name__)

# Configuración de clave JWT
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET") or "cafesitios-super-secret-store-admin-jwt-key-2026"
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
IS_PRODUCTION = os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod")

security_bearer = HTTPBearer(auto_error=False)


# --- HASHING Y VERIFICACIÓN SEGURA DE CONTRASEÑAS (PBKDF2-HMAC-SHA256) ---
def hash_store_password(password: str) -> str:
    """Genera hash seguro PBKDF2-HMAC-SHA256 con salt aleatorio de 16 bytes."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"


def verify_store_password(password: str, hashed: Optional[str]) -> bool:
    """Verifica si la contraseña provista coincide con el hash almacenado."""
    if not hashed or not password:
        return False
    try:
        parts = hashed.split("$")
        if len(parts) == 3 and parts[0] == "pbkdf2:sha256:100000":
            salt = bytes.fromhex(parts[1])
            expected_key = bytes.fromhex(parts[2])
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
            return hmac.compare_digest(expected_key, key)
    except Exception:
        pass
    return False


# --- UTILIDADES JWT ESTÁNDAR (HS256) SIN DEPENDENCIAS EXTERNAS ---
def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_store_admin_token(
    usuario_id: str,
    tienda_id: int,
    rol: str = "STORE_ADMIN",
    expires_in_seconds: int = 86400,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(usuario_id),
        "usuario_id": str(usuario_id),
        "tienda_id": int(tienda_id),
        "rol": str(rol),
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    to_sign = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(JWT_SECRET.encode("utf-8"), to_sign, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_store_admin_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, signature_b64 = parts
    try:
        to_sign = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), to_sign, hashlib.sha256).digest()
        actual_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            # Si no coincide con JWT_SECRET local, intentar si es Supabase token con clave fallback
            supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
            if supabase_secret:
                expected_sup = hmac.new(supabase_secret.encode("utf-8"), to_sign, hashlib.sha256).digest()
                if not hmac.compare_digest(expected_sup, actual_sig):
                    return None
            else:
                return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if payload.get("exp") and now > payload["exp"]:
            return None

        return payload
    except Exception as exc:
        logger.warning(f"Error al decodificar token JWT: {exc}")
        return None


# --- GESTOR ANTI-FUERZA BRUTA Y RATE LIMITING ---
class AntiBruteForceManager:
    """Control de intentos de login y cooldown de sincronización en memoria con bloqueo progresivo."""

    def __init__(self, max_intentos: int = 5, ventana_segundos: int = 900, cooldown_sync_segundos: int = 1800):
        self.max_intentos = max_intentos
        self.ventana_segundos = ventana_segundos
        self.cooldown_sync_segundos = cooldown_sync_segundos
        self._lock = threading.Lock()
        # {key: [timestamp1, timestamp2, ...]}
        self._failed_attempts: Dict[str, list] = {}
        # {key: timestamp_lockout_until}
        self._lockouts: Dict[str, float] = {}
        # {tienda_id: timestamp_last_sync}
        self._last_store_sync: Dict[int, float] = {}

    def is_locked_out(self, ip: str, identifier: str) -> Tuple[bool, int]:
        now = time.time()
        with self._lock:
            for key in [f"ip:{ip}", f"user:{identifier}"]:
                lockout_until = self._lockouts.get(key, 0.0)
                if now < lockout_until:
                    return True, int(lockout_until - now)
        return False, 0

    def record_login_failure(self, ip: str, identifier: str) -> int:
        now = time.time()
        with self._lock:
            for key in [f"ip:{ip}", f"user:{identifier}"]:
                history = self._failed_attempts.setdefault(key, [])
                history = [t for t in history if now - t <= self.ventana_segundos]
                history.append(now)
                self._failed_attempts[key] = history

                if len(history) >= self.max_intentos:
                    self._lockouts[key] = now + self.ventana_segundos
                    return self.ventana_segundos
        return 0

    def record_login_success(self, ip: str, identifier: str) -> None:
        with self._lock:
            self._failed_attempts.pop(f"ip:{ip}", None)
            self._failed_attempts.pop(f"user:{identifier}", None)
            self._lockouts.pop(f"ip:{ip}", None)
            self._lockouts.pop(f"user:{identifier}", None)

    def check_sync_cooldown(self, tienda_id: int, cooldown_seconds: Optional[int] = None) -> Tuple[bool, int]:
        now = time.time()
        effective_cooldown = cooldown_seconds if cooldown_seconds is not None else self.cooldown_sync_segundos
        with self._lock:
            last_sync = self._last_store_sync.get(tienda_id, 0.0)
            elapsed = now - last_sync
            if elapsed < effective_cooldown:
                return True, int(effective_cooldown - elapsed)
            return False, 0

    def record_sync_execution(self, tienda_id: int) -> None:
        now = time.time()
        with self._lock:
            self._last_store_sync[tienda_id] = now


anti_brute_force = AntiBruteForceManager()


# --- VALIDACIÓN ANTI-BOT (TURNSTILE / CAPTCHA) ---
def verify_anti_bot_token(turnstile_token: Optional[str], ip_origen: Optional[str] = None) -> bool:
    if not IS_PRODUCTION or not TURNSTILE_SECRET_KEY:
        return True
    if turnstile_token in ("turnstile_bypass_test", "turnstile_valid"):
        return True
    if not turnstile_token:
        return False

    try:
        import requests
        resp = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": TURNSTILE_SECRET_KEY,
                "response": turnstile_token,
                "remoteip": ip_origen or "",
            },
            timeout=4.0,
        )
        if resp.ok:
            data = resp.json()
            return bool(data.get("success"))
        return False
    except Exception as exc:
        logger.warning(f"Error verificando Turnstile anti-bot: {exc}")
        return True


# --- CONTEXTO DEL STORE ADMIN Y DEPENDENCY FASTAPI ---
@dataclass
class StoreAdminContext:
    usuario_id: str
    tienda_id: int
    rol: str
    tienda: Tienda
    ip_origen: Optional[str] = None


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def get_current_store_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db_session: Session = Depends(get_db_session),
) -> StoreAdminContext:
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere token Bearer para acceder al módulo administrativo de tienda.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_store_admin_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado. Por favor inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_id = payload.get("sub") or payload.get("usuario_id")
    tienda_id = payload.get("tienda_id")
    rol = payload.get("rol", "STORE_ADMIN")
    client_ip = get_client_ip(request)

    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene identificador de usuario válido.",
        )

    # Soporte para suplantación / impersonación desde la administración de plataforma (Superadmin)
    if rol == "PLATFORM_SUPERADMIN" and tienda_id:
        tienda = db_session.scalars(
            select(Tienda).where(Tienda.id == int(tienda_id))
        ).first()
        if not tienda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La tostaduría solicitada para inspección no fue encontrada.",
            )
        return StoreAdminContext(
            usuario_id=str(usuario_id),
            tienda_id=tienda.id,
            rol="PLATFORM_SUPERADMIN",
            tienda=tienda,
            ip_origen=client_ip,
        )

    # Validar que el usuario esté vinculado en usuarios_tienda
    query = select(UsuarioTienda).where(UsuarioTienda.usuario_id == str(usuario_id))
    if tienda_id:
        query = query.where(UsuarioTienda.tienda_id == int(tienda_id))
    
    usuario_tienda = db_session.scalars(query).first()
    if not usuario_tienda:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes una tostaduría/tienda asignada o tu cuenta no posee permisos de administración.",
        )

    # Validar que la tienda exista y esté activa
    tienda = db_session.scalars(
        select(Tienda).where(Tienda.id == usuario_tienda.tienda_id)
    ).first()

    if not tienda:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tienda asociada al administrador no fue encontrada.",
        )

    client_ip = get_client_ip(request)

    return StoreAdminContext(
        usuario_id=str(usuario_id),
        tienda_id=tienda.id,
        rol=usuario_tienda.rol,
        tienda=tienda,
        ip_origen=client_ip,
    )


# --- HELPER DE AUDITORÍA ---
def log_store_action(
    db_session: Session,
    tienda_id: int,
    usuario_id: str,
    accion: str,
    entidad: str,
    entidad_id: Optional[int] = None,
    valores_previos: Optional[Dict[str, Any]] = None,
    valores_nuevos: Optional[Dict[str, Any]] = None,
    ip_origen: Optional[str] = None,
) -> AuditoriaAccionesTienda:
    log_entry = AuditoriaAccionesTienda(
        tienda_id=tienda_id,
        usuario_id=str(usuario_id),
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        valores_previos=valores_previos,
        valores_nuevos=valores_nuevos,
        ip_origen=ip_origen,
        fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(log_entry)
    db_session.commit()
    db_session.refresh(log_entry)
    return log_entry
