"""Caso de Uso: Telemetría, Clics Salientes y Registro de Búsquedas (Sección 5 y 7).

Anonimiza la IP con SHA-256 y persiste interacciones_clics e historial_busquedas.
"""

import hashlib
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.database import HistorialBusqueda, InteraccionClic, Producto, Tienda



class ManageTelemetryUseCase:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()

    def record_click_event(
        self,
        tipo_evento: str,
        client_ip: str,
        producto_id: Optional[int] = None,
        variante_id: Optional[int] = None,
        metadata_evento: Optional[Dict[str, Any]] = None,
    ) -> InteraccionClic:
        ip_hash = self.hash_ip(client_ip)
        meta = dict(metadata_evento or {})

        # Resiliencia: si producto_id no vino, intentar asociar por metadata
        if not producto_id:
            dest_url = meta.get("destination_url") or meta.get("url")
            p_name = meta.get("product_name") or meta.get("item_name")
            s_name = meta.get("store_name") or meta.get("item_brand")
            if dest_url:
                try:
                    p = self.session.execute(
                        select(Producto.id).where(Producto.url_detalle == str(dest_url))
                    ).scalars().first()
                    if p:
                        producto_id = p
                except Exception:
                    pass
            if not producto_id and p_name and s_name:
                try:
                    p = self.session.execute(
                        select(Producto.id)
                        .join(Tienda, Tienda.id == Producto.tienda_id)
                        .where(Producto.nombre.ilike(str(p_name).strip()), Tienda.nombre.ilike(str(s_name).strip()))
                    ).scalars().first()
                    if p:
                        producto_id = p
                except Exception:
                    pass

        # Si tenemos producto_id, garantizar que meta tenga tienda_id y store_id
        if producto_id:
            try:
                t_id = self.session.execute(
                    select(Producto.tienda_id).where(Producto.id == producto_id)
                ).scalar_one_or_none()
                if t_id:
                    meta.setdefault("tienda_id", t_id)
                    meta.setdefault("store_id", t_id)
            except Exception:
                pass
        elif "store_id" in meta and "tienda_id" not in meta:
            meta["tienda_id"] = meta["store_id"]
        elif "tienda_id" in meta and "store_id" not in meta:
            meta["store_id"] = meta["tienda_id"]

        interaccion = InteraccionClic(
            producto_id=producto_id,
            variante_id=variante_id,
            tipo_evento=tipo_evento,
            ip_hash=ip_hash,
            metadata_evento=meta,
        )
        self.session.add(interaccion)
        self.session.commit()
        self.session.refresh(interaccion)
        return interaccion

    def record_search_query(
        self,
        termino_busqueda: str,
        resultados_encontrados: int = 0,
    ) -> HistorialBusqueda:
        busqueda = HistorialBusqueda(
            termino_busqueda=termino_busqueda.strip()[:255],
            resultados_encontrados=resultados_encontrados,
        )
        self.session.add(busqueda)
        self.session.commit()
        self.session.refresh(busqueda)
        return busqueda

