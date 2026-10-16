"""Caso de Uso: Telemetría, Clics Salientes y Registro de Búsquedas (Sección 5 y 7).

Anonimiza la IP con SHA-256 y persiste interacciones_clics e historial_busquedas.
"""

import hashlib
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from db.database import HistorialBusqueda, InteraccionClic


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
        interaccion = InteraccionClic(
            producto_id=producto_id,
            variante_id=variante_id,
            tipo_evento=tipo_evento,
            ip_hash=ip_hash,
            metadata_evento=metadata_evento or {},
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

