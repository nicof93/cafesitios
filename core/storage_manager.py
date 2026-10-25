import os
from typing import Any, Dict, Optional


def get_tienda_storage_info(tienda_id: int, limite_mb: Optional[int] = None) -> Dict[str, Any]:
    """Calcula el uso de almacenamiento en MB de las imágenes subidas por una tostaduría."""
    upload_dir = os.path.join("static", "uploads", "productos")
    total_bytes = 0
    total_archivos = 0
    prefix = f"{tienda_id}_"
    if os.path.isdir(upload_dir):
        for entry in os.scandir(upload_dir):
            if entry.is_file() and entry.name.startswith(prefix):
                try:
                    total_bytes += entry.stat().st_size
                    total_archivos += 1
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

