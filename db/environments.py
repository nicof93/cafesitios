from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text

from db.config import settings

logger = logging.getLogger(__name__)

CONFIG_FILE_PATH = Path(__file__).resolve().parent.parent / "ambientes.json"


def _get_default_environments() -> List[Dict[str, Any]]:
    supabase_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""
    return [
        {
            "id": "local",
            "nombre": "PostgreSQL Local",
            "descripcion": "Base de datos local de desarrollo en Docker o PostgreSQL local.",
            "tipo": "postgres",
            "connection_url": settings.database_url,
            "color_badge": "amber",
            "activo": True,
            "es_protegido": False,
            "es_sistema": True,
        },
        {
            "id": "supabase",
            "nombre": "Supabase Producción",
            "descripcion": "Base de datos PostgreSQL en la nube (Supabase Cloud).",
            "tipo": "supabase",
            "connection_url": supabase_url,
            "color_badge": "red",
            "activo": True,
            "es_protegido": True,
            "es_sistema": True,
        },
    ]


class EnvironmentManager:
    """Administrador local de ambientes de base de datos multi-entorno."""

    @classmethod
    def _read_config(cls) -> List[Dict[str, Any]]:
        if not CONFIG_FILE_PATH.exists():
            defaults = _get_default_environments()
            cls._write_config(defaults)
            return defaults

        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"Error al leer ambientes.json ({e}). Retornando valores predeterminados.")
        return _get_default_environments()

    @classmethod
    def _write_config(cls, environments: List[Dict[str, Any]]) -> None:
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(environments, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error al guardar ambientes.json: {e}")

    @classmethod
    def list_environments(cls, mask_secrets: bool = True) -> List[Dict[str, Any]]:
        envs = cls._read_config()
        # Verificar que 'local' y 'supabase' estén presentes
        existing_ids = {e.get("id") for e in envs}
        defaults = _get_default_environments()
        changed = False

        for default_env in defaults:
            if default_env["id"] not in existing_ids:
                envs.append(default_env)
                changed = True
            else:
                # Actualizar URL del sistema si viene de variables de entorno frescas
                for e in envs:
                    if e["id"] == "local" and not e.get("connection_url"):
                        e["connection_url"] = settings.database_url
                        changed = True
                    elif e["id"] == "supabase" and not e.get("connection_url") and default_env["connection_url"]:
                        e["connection_url"] = default_env["connection_url"]
                        changed = True

        if changed:
            cls._write_config(envs)

        result = []
        for e in envs:
            item = dict(e)
            if mask_secrets and item.get("connection_url"):
                raw_url = item["connection_url"]
                # Enmascarar contraseña en la URL para visualización segura en API
                if "@" in raw_url and "://" in raw_url:
                    prefix, rest = raw_url.split("://", 1)
                    if ":" in rest and "@" in rest:
                        user_pass, host_db = rest.split("@", 1)
                        user = user_pass.split(":")[0]
                        item["connection_url_masked"] = f"{prefix}://{user}:******@{host_db}"
                    else:
                        item["connection_url_masked"] = raw_url
                else:
                    item["connection_url_masked"] = raw_url
            result.append(item)
        return result

    @classmethod
    def get_environment(cls, env_id: str) -> Optional[Dict[str, Any]]:
        envs = cls.list_environments(mask_secrets=False)
        for e in envs:
            if e.get("id") == env_id:
                return e
        return None

    @classmethod
    def get_connection_url(cls, env_id: Optional[str] = None) -> str:
        """Retorna la cadena de conexión para el ambiente solicitado, o el predeterminado."""
        if not env_id or env_id == "local":
            return settings.database_url

        env = cls.get_environment(env_id)
        if env and env.get("connection_url"):
            return env["connection_url"]

        # Fallback a local si no se encontró o no tiene URL
        logger.warning(f"Ambiente '{env_id}' no encontrado o sin connection_url. Usando 'local'.")
        return settings.database_url

    @classmethod
    def save_environment(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea o actualiza un ambiente de base de datos."""
        envs = cls.list_environments(mask_secrets=False)
        env_id = data.get("id", "").strip().lower()
        if not env_id:
            raise ValueError("El 'id' del ambiente es obligatorio.")

        existing_index = next((i for i, e in enumerate(envs) if e.get("id") == env_id), -1)

        payload = {
            "id": env_id,
            "nombre": data.get("nombre", env_id).strip(),
            "descripcion": data.get("descripcion", "").strip(),
            "tipo": data.get("tipo", "postgres").strip().lower(),
            "connection_url": data.get("connection_url", "").strip(),
            "color_badge": data.get("color_badge", "emerald"),
            "activo": bool(data.get("activo", True)),
            "es_protegido": bool(data.get("es_protegido", False)),
            "es_sistema": False,
        }

        if existing_index >= 0:
            # Preservar si es sistema
            if envs[existing_index].get("es_sistema"):
                payload["es_sistema"] = True
                if not payload["connection_url"]:
                    payload["connection_url"] = envs[existing_index].get("connection_url", "")
            envs[existing_index] = payload
        else:
            envs.append(payload)

        cls._write_config(envs)
        return payload

    @classmethod
    def update_environment(cls, env_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza un ambiente existente (local, supabase o personalizado)."""
        envs = cls.list_environments(mask_secrets=False)
        clean_id = env_id.strip().lower()
        existing_index = next((i for i, e in enumerate(envs) if e.get("id") == clean_id), -1)
        if existing_index < 0:
            raise ValueError(f"Ambiente '{env_id}' no encontrado.")

        current = envs[existing_index]

        if "nombre" in data and data["nombre"]:
            current["nombre"] = data["nombre"].strip()
        if "descripcion" in data and data["descripcion"] is not None:
            current["descripcion"] = data["descripcion"].strip()
        if "tipo" in data and data["tipo"]:
            current["tipo"] = data["tipo"].strip().lower()
        if "connection_url" in data and data["connection_url"]:
            current["connection_url"] = data["connection_url"].strip()
        if "color_badge" in data and data["color_badge"]:
            current["color_badge"] = data["color_badge"].strip()
        if "activo" in data and data["activo"] is not None:
            current["activo"] = bool(data["activo"])
        if "es_protegido" in data and data["es_protegido"] is not None:
            current["es_protegido"] = bool(data["es_protegido"])

        cls._write_config(envs)

        # Invalidar caché en DatabaseManager si cambió la conexión
        try:
            from db.database import DatabaseManager
            if clean_id in DatabaseManager._instances:
                del DatabaseManager._instances[clean_id]
        except Exception:
            pass

        return current

    @classmethod
    def delete_environment(cls, env_id: str) -> bool:
        """Elimina un ambiente (no se pueden eliminar ambientes de sistema como 'local')."""
        envs = cls.list_environments(mask_secrets=False)
        for i, e in enumerate(envs):
            if e.get("id") == env_id:
                if e.get("es_sistema"):
                    raise ValueError(f"El ambiente de sistema '{env_id}' no puede ser eliminado.")
                envs.pop(i)
                cls._write_config(envs)
                return True
        return False

    @classmethod
    def test_connection(cls, env_id: str) -> Dict[str, Any]:
        """Prueba la conexión a la base de datos del ambiente y calcula la latencia."""
        env = cls.get_environment(env_id)
        if not env:
            return {"success": False, "error": f"Ambiente '{env_id}' no existe."}

        url = env.get("connection_url")
        if not url:
            return {"success": False, "error": f"El ambiente '{env['nombre']}' no tiene configurada una URL de conexión."}

        connect_args = {} if str(url).startswith("sqlite") else {"prepare_threshold": None}
        start_time = time.perf_counter()
        try:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
            with engine.connect() as conn:
                res = conn.execute(text("SELECT 1")).scalar()
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "success": True,
                    "env_id": env_id,
                    "nombre": env["nombre"],
                    "latency_ms": latency_ms,
                    "message": f"Conexión exitosa a {env['nombre']} ({latency_ms} ms).",
                }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "env_id": env_id,
                "nombre": env["nombre"],
                "latency_ms": latency_ms,
                "error": str(e),
            }

