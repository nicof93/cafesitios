import os
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from db.database import Tienda


def get_all_tiendas_images_storage(upload_dir: str = os.path.join("static", "uploads", "productos")) -> Dict[int, Dict[str, int]]:
    """Escanea el directorio de subidas una sola vez y agrupa bytes y archivos por tienda_id."""
    res: Dict[int, Dict[str, int]] = {}
    if not os.path.isdir(upload_dir):
        return res

    pattern = re.compile(r"^(\d+)_")
    try:
        for entry in os.scandir(upload_dir):
            if entry.is_file():
                match = pattern.match(entry.name)
                if match:
                    try:
                        t_id = int(match.group(1))
                        size = entry.stat().st_size
                        if t_id not in res:
                            res[t_id] = {"bytes": 0, "archivos": 0}
                        res[t_id]["bytes"] += size
                        res[t_id]["archivos"] += 1
                    except (ValueError, OSError):
                        pass
    except OSError:
        pass

    return res


def get_tienda_storage_info(tienda_id: int, limite_mb: Optional[int] = None) -> Dict[str, Any]:
    """Calcula el uso de almacenamiento en MB de las imágenes subidas por una tostaduría específica."""
    upload_dir = os.path.join("static", "uploads", "productos")
    total_bytes = 0
    total_archivos = 0
    prefix = f"{tienda_id}_"
    if os.path.isdir(upload_dir):
        try:
            for entry in os.scandir(upload_dir):
                if entry.is_file() and entry.name.startswith(prefix):
                    try:
                        total_bytes += entry.stat().st_size
                        total_archivos += 1
                    except OSError:
                        pass
        except OSError:
            pass

    lim_mb = limite_mb if (limite_mb and limite_mb > 0) else 250
    lim_bytes = lim_mb * 1024 * 1024
    mb_usados = round(total_bytes / (1024 * 1024), 2)
    porcentaje = round((total_bytes / lim_bytes) * 100, 1) if lim_bytes > 0 else 0.0

    return {
        "tienda_id": tienda_id,
        "bytes_usados": total_bytes,
        "mb_usados": mb_usados,
        "limite_mb": lim_mb,
        "porcentaje_usado": min(porcentaje, 100.0),
        "total_archivos": total_archivos,
        "superado": total_bytes >= lim_bytes,
    }


def calcular_reporte_almacenamiento_global(session: Session) -> Dict[str, Any]:
    """Genera un reporte consolidado del almacenamiento de imágenes y peso de datos en BD para todas las tiendas."""
    tiendas_orm = session.scalars(select(Tienda).order_by(Tienda.nombre.asc())).all()
    mapa_imagenes = get_all_tiendas_images_storage()

    bind = session.get_bind()
    is_postgres = (bind is not None and getattr(bind.dialect, "name", "") == "postgresql")

    # Contenedores de desglose por tienda
    # {tienda_id: {"productos": {"filas": 0, "bytes": 0}, ...}}
    desglose_por_tienda: Dict[int, Dict[str, Dict[str, int]]] = {
        t.id: {
            "productos": {"filas": 0, "bytes": 0},
            "variantes": {"filas": 0, "bytes": 0},
            "historial_precios": {"filas": 0, "bytes": 0},
            "auditoria_acciones": {"filas": 0, "bytes": 0},
            "recetas": {"filas": 0, "bytes": 0},
            "sucursales": {"filas": 0, "bytes": 0},
            "sincronizaciones": {"filas": 0, "bytes": 0},
            "otros": {"filas": 0, "bytes": 0},
        }
        for t in tiendas_orm
    }

    if is_postgres:
        queries = {
            "productos": """
                SELECT p.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(p.*)), 0) as bytes
                FROM productos p GROUP BY p.tienda_id
            """,
            "variantes": """
                SELECT p.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(v.*)), 0) as bytes
                FROM variantes v JOIN productos p ON v.producto_id = p.id GROUP BY p.tienda_id
            """,
            "historial_precios": """
                SELECT p.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(h.*)), 0) as bytes
                FROM historial_precios h 
                JOIN variantes v ON h.variante_id = v.id 
                JOIN productos p ON v.producto_id = p.id 
                GROUP BY p.tienda_id
            """,
            "auditoria_acciones": """
                SELECT a.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(a.*)), 0) as bytes
                FROM auditoria_acciones_tienda a GROUP BY a.tienda_id
            """,
            "recetas": """
                SELECT r.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(r.*)), 0) as bytes
                FROM recetas r GROUP BY r.tienda_id
            """,
            "sucursales": """
                SELECT s.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(s.*)), 0) as bytes
                FROM sucursales_tienda s GROUP BY s.tienda_id
            """,
            "sincronizaciones": """
                SELECT s.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(s.*)), 0) as bytes
                FROM sincronizaciones s GROUP BY s.tienda_id
            """,
            "otros": """
                SELECT o.tienda_id, COUNT(*) as filas, COALESCE(SUM(pg_column_size(o.*)), 0) as bytes
                FROM ofertas_tienda o GROUP BY o.tienda_id
            """,
        }
        for key, query_str in queries.items():
            try:
                rows = session.execute(text(query_str)).fetchall()
                for row in rows:
                    t_id = row[0]
                    filas = int(row[1]) if row[1] else 0
                    bytes_val = int(row[2]) if row[2] else 0
                    if t_id in desglose_por_tienda and key in desglose_por_tienda[t_id]:
                        desglose_por_tienda[t_id][key] = {"filas": filas, "bytes": bytes_val}
            except Exception:
                pass
    else:
        # Fallback analítico para SQLite (utilizado en testing unitario)
        sqlite_queries = {
            "productos": """
                SELECT p.tienda_id, COUNT(*) as filas, 
                       COALESCE(SUM(LENGTH(p.nombre) + LENGTH(COALESCE(p.descripcion, '')) + 256), 0) as bytes
                FROM productos p GROUP BY p.tienda_id
            """,
            "variantes": """
                SELECT p.tienda_id, COUNT(*) as filas, 
                       COALESCE(SUM(LENGTH(COALESCE(v.opcion, '')) + 128), 0) as bytes
                FROM variantes v JOIN productos p ON v.producto_id = p.id GROUP BY p.tienda_id
            """,
            "historial_precios": """
                SELECT p.tienda_id, COUNT(*) as filas, 
                       COALESCE(COUNT(*) * 64, 0) as bytes
                FROM historial_precios h 
                JOIN variantes v ON h.variante_id = v.id 
                JOIN productos p ON v.producto_id = p.id 
                GROUP BY p.tienda_id
            """,
            "auditoria_acciones": """
                SELECT a.tienda_id, COUNT(*) as filas, 
                       COALESCE(SUM(LENGTH(COALESCE(a.accion, '')) + LENGTH(COALESCE(a.detalles_json, '')) + 64), 0) as bytes
                FROM auditoria_acciones_tienda a GROUP BY a.tienda_id
            """,
            "recetas": """
                SELECT r.tienda_id, COUNT(*) as filas, 
                       COALESCE(SUM(LENGTH(COALESCE(r.nombre, '')) + LENGTH(COALESCE(r.descripcion, '')) + 128), 0) as bytes
                FROM recetas r GROUP BY r.tienda_id
            """,
            "sucursales": """
                SELECT s.tienda_id, COUNT(*) as filas, 
                       COALESCE(SUM(LENGTH(COALESCE(s.nombre, '')) + LENGTH(COALESCE(s.direccion, '')) + 128), 0) as bytes
                FROM sucursales_tienda s GROUP BY s.tienda_id
            """,
            "sincronizaciones": """
                SELECT s.tienda_id, COUNT(*) as filas, 
                       COALESCE(COUNT(*) * 128, 0) as bytes
                FROM sincronizaciones s GROUP BY s.tienda_id
            """,
            "otros": """
                SELECT o.tienda_id, COUNT(*) as filas, 
                       COALESCE(COUNT(*) * 64, 0) as bytes
                FROM ofertas_tienda o GROUP BY o.tienda_id
            """,
        }
        for key, query_str in sqlite_queries.items():
            try:
                rows = session.execute(text(query_str)).fetchall()
                for row in rows:
                    t_id = row[0]
                    filas = int(row[1]) if row[1] else 0
                    bytes_val = int(row[2]) if row[2] else 0
                    if t_id in desglose_por_tienda and key in desglose_por_tienda[t_id]:
                        desglose_por_tienda[t_id][key] = {"filas": filas, "bytes": bytes_val}
            except Exception:
                pass

    tiendas_resultado: List[Dict[str, Any]] = []
    total_global_imagenes_archivos = 0
    total_global_imagenes_bytes = 0
    total_global_bd_filas = 0
    total_global_bd_bytes = 0

    tienda_mayor_img: Optional[Dict[str, Any]] = None
    tienda_mayor_bd: Optional[Dict[str, Any]] = None

    for t in tiendas_orm:
        t_id = t.id
        img_data = mapa_imagenes.get(t_id, {"bytes": 0, "archivos": 0})
        img_bytes = img_data["bytes"]
        img_archivos = img_data["archivos"]
        img_mb = round(img_bytes / (1024 * 1024), 2)

        lim_mb = t.limite_almacenamiento_mb if (t.limite_almacenamiento_mb and t.limite_almacenamiento_mb > 0) else 250
        lim_bytes = lim_mb * 1024 * 1024
        porcentaje_cuota = round((img_bytes / lim_bytes) * 100, 1) if lim_bytes > 0 else 0.0

        if porcentaje_cuota >= 100.0:
            estado_cuota = "superado"
        elif porcentaje_cuota >= 80.0:
            estado_cuota = "advertencia"
        else:
            estado_cuota = "normal"

        desglose = desglose_por_tienda.get(t_id, {})
        bd_filas = sum(item["filas"] for item in desglose.values())
        bd_bytes = sum(item["bytes"] for item in desglose.values())
        bd_kb = round(bd_bytes / 1024, 2)
        bd_mb = round(bd_bytes / (1024 * 1024), 3)

        peso_total_mb = round(img_mb + bd_mb, 2)

        total_global_imagenes_archivos += img_archivos
        total_global_imagenes_bytes += img_bytes
        total_global_bd_filas += bd_filas
        total_global_bd_bytes += bd_bytes

        tienda_item = {
            "tienda_id": t_id,
            "nombre": t.nombre,
            "url_base": t.url_base,
            "plataforma": t.plataforma,
            "activo": bool(t.activo),
            "logo_url": t.logo_url,
            "limite_almacenamiento_mb": lim_mb,
            "imagenes": {
                "total_archivos": img_archivos,
                "peso_bytes": img_bytes,
                "peso_mb": img_mb,
                "porcentaje_usado": min(porcentaje_cuota, 100.0),
                "estado_cuota": estado_cuota,
            },
            "base_datos": {
                "total_filas": bd_filas,
                "peso_bytes": bd_bytes,
                "peso_kb": bd_kb,
                "peso_mb": bd_mb,
                "desglose_tablas": desglose,
            },
            "peso_total_mb": peso_total_mb,
        }
        tiendas_resultado.append(tienda_item)

        if tienda_mayor_img is None or img_bytes > tienda_mayor_img["peso_imagenes_bytes"]:
            tienda_mayor_img = {
                "tienda_id": t_id,
                "nombre": t.nombre,
                "peso_imagenes_bytes": img_bytes,
                "peso_imagenes_mb": img_mb,
            }

        if tienda_mayor_bd is None or bd_bytes > tienda_mayor_bd["peso_bd_bytes"]:
            tienda_mayor_bd = {
                "tienda_id": t_id,
                "nombre": t.nombre,
                "peso_bd_bytes": bd_bytes,
                "peso_bd_mb": bd_mb,
            }

    total_imagenes_mb = round(total_global_imagenes_bytes / (1024 * 1024), 2)
    total_bd_mb = round(total_global_bd_bytes / (1024 * 1024), 2)
    total_combinado_mb = round(total_imagenes_mb + total_bd_mb, 2)

    resumen_global = {
        "total_tiendas": len(tiendas_resultado),
        "total_imagenes": total_global_imagenes_archivos,
        "total_imagenes_mb": total_imagenes_mb,
        "total_filas_bd": total_global_bd_filas,
        "total_bd_mb": total_bd_mb,
        "total_combinado_mb": total_combinado_mb,
        "tienda_mayor_consumo_imagenes": tienda_mayor_img,
        "tienda_mayor_consumo_bd": tienda_mayor_bd,
    }

    return {
        "resumen_global": resumen_global,
        "tiendas": tiendas_resultado,
    }
