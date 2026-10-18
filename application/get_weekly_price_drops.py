import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import HistorialPrecio, Producto, Tienda, Variante

logger = logging.getLogger(__name__)


def _extract_root_domain(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    except Exception:
        pass
    return cleaned


class GetWeeklyPriceDropsUseCase:
    """Caso de uso para consultar las mayores caídas de precio de la semana (Ofertas Verificadas)."""

    def __init__(self, db_session: Session):
        self.session = db_session

    def execute(self, limit: int = 10, dias: int = 7) -> List[Dict[str, Any]]:
        is_postgres = self.session.bind and self.session.bind.dialect.name == 'postgresql'
        
        # 1. Intentar llamar a la función optimizada de PostgreSQL si está disponible
        if is_postgres:
            try:
                sql = text("SELECT * FROM fn_obtener_mayores_caidas_semana(:limite, :dias)")
                result = self.session.execute(sql, {"limite": limit, "dias": dias})
                rows = result.mappings().all()
                if rows:
                    items = []
                    for r in rows:
                        items.append({
                            "oferta_id": int(r["oferta_id"]),
                            "producto_id": int(r["producto_id"]),
                            "nombre_producto": str(r["nombre_producto"]),
                            "tienda": str(r["tienda"]),
                            "url_tienda": _extract_root_domain(r.get("url_tienda")),
                            "imagen_url": r.get("imagen_url"),
                            "formato_gramos": int(r.get("formato_gramos") or 250),
                            "precio_anterior": int(r["precio_anterior"]),
                            "precio_actual": int(r["precio_actual"]),
                            "precio_por_kilo": float(r["precio_por_kilo"]),
                            "monto_rebaja": int(r["monto_rebaja"]),
                            "porcentaje_descuento": int(r["porcentaje_descuento"]),
                            "link_detalle": str(r.get("link_detalle") or f"/product/{r['producto_id']}"),
                            "fecha_cambio": r.get("fecha_cambio")
                        })
                    return items
            except Exception as e:
                logger.warning(f"Error invocando fn_obtener_mayores_caidas_semana, usando fallback ORM: {e}")

        # 2. Fallback en Python / SQLAlchemy (Universal para PostgreSQL y SQLite)
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dias)

        # Consultar historial en la ventana de tiempo
        history_records = (
            self.session.query(HistorialPrecio)
            .join(Variante, HistorialPrecio.variante_id == Variante.id)
            .join(Producto, Variante.producto_id == Producto.id)
            .join(Tienda, Producto.tienda_id == Tienda.id)
            .filter(
                HistorialPrecio.fecha_registro >= cutoff_date,
                Producto.activo.is_(True),
                Producto.oculto_catalogo.is_(False),
                Tienda.activo.is_(True),
                Variante.disponible.is_(True),
            )
            .order_by(HistorialPrecio.variante_id, HistorialPrecio.fecha_registro.asc(), HistorialPrecio.id.asc())
            .all()
        )

        drops_by_variant: Dict[int, Dict[str, Any]] = {}

        # Mapear primer y último precio por variante en la ventana
        variant_bounds: Dict[int, Dict[str, Any]] = {}
        for hp in history_records:
            v_id = hp.variante_id
            if v_id not in variant_bounds:
                variant_bounds[v_id] = {
                    "first_price": hp.precio_clp,
                    "first_date": hp.fecha_registro,
                    "last_price": hp.precio_clp,
                    "last_kilo": float(hp.precio_por_kilo or 0.0),
                    "last_date": hp.fecha_registro,
                    "variant": hp.variante,
                }
            else:
                variant_bounds[v_id]["last_price"] = hp.precio_clp
                variant_bounds[v_id]["last_kilo"] = float(hp.precio_por_kilo or 0.0)
                variant_bounds[v_id]["last_date"] = hp.fecha_registro

        for v_id, data in variant_bounds.items():
            p_ini = data["first_price"]
            p_fin = data["last_price"]
            if p_ini > p_fin and (p_ini - p_fin) > 0:
                variant: Variante = data["variant"]
                product: Producto = variant.producto
                store: Tienda = product.tienda
                monto = p_ini - p_fin
                pct = round(((p_ini - p_fin) / p_ini) * 100)
                
                store_url = getattr(store, 'sitio_oficial', None) or getattr(store, 'url_web', None) or store.url_base
                root_site = _extract_root_domain(store_url)

                drops_by_variant[v_id] = {
                    "oferta_id": variant.id,
                    "producto_id": product.id,
                    "nombre_producto": product.nombre,
                    "tienda": store.nombre,
                    "url_tienda": root_site,
                    "imagen_url": product.imagen,
                    "formato_gramos": variant.formato_gramos,
                    "precio_anterior": p_ini,
                    "precio_actual": p_fin,
                    "precio_por_kilo": data["last_kilo"] or float(variant.precio_por_kilo),
                    "monto_rebaja": monto,
                    "porcentaje_descuento": pct,
                    "link_detalle": product.url_detalle or f"/product/{product.id}",
                    "fecha_cambio": data["last_date"]
                }

        # Si hay pocas variantes con historial reciente (ej. catálogo recién importado o en tests),
        # complementar con variantes marcadas explícitamente en oferta donde precio_original_clp > precio_clp
        if len(drops_by_variant) < limit:
            on_sale_variants = (
                self.session.query(Variante)
                .join(Producto, Variante.producto_id == Producto.id)
                .join(Tienda, Producto.tienda_id == Tienda.id)
                .filter(
                    Variante.disponible.is_(True),
                    Variante.precio_original_clp > Variante.precio_clp,
                    Producto.activo.is_(True),
                    Producto.oculto_catalogo.is_(False),
                    Tienda.activo.is_(True),
                )
                .order_by((Variante.precio_original_clp - Variante.precio_clp).desc())
                .limit(limit * 2)
                .all()
            )

            for var in on_sale_variants:
                if var.id in drops_by_variant:
                    continue
                p_orig = var.precio_original_clp
                p_curr = var.precio_clp
                if p_orig > p_curr:
                    prod = var.producto
                    st = prod.tienda
                    monto = p_orig - p_curr
                    pct = round(((p_orig - p_curr) / p_orig) * 100)
                    st_url = getattr(st, 'sitio_oficial', None) or getattr(st, 'url_web', None) or st.url_base
                    root_site = _extract_root_domain(st_url)
                    
                    drops_by_variant[var.id] = {
                        "oferta_id": var.id,
                        "producto_id": prod.id,
                        "nombre_producto": prod.nombre,
                        "tienda": st.nombre,
                        "url_tienda": root_site,
                        "imagen_url": prod.imagen,
                        "formato_gramos": var.formato_gramos,
                        "precio_anterior": p_orig,
                        "precio_actual": p_curr,
                        "precio_por_kilo": float(var.precio_por_kilo),
                        "monto_rebaja": monto,
                        "porcentaje_descuento": pct,
                        "link_detalle": prod.url_detalle or f"/product/{prod.id}",
                        "fecha_cambio": var.fecha_actualizacion
                    }

        sorted_drops = sorted(
            drops_by_variant.values(),
            key=lambda x: (x["porcentaje_descuento"], x["monto_rebaja"]),
            reverse=True
        )

        return sorted_drops[:limit]
