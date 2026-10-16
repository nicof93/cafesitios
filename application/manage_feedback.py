"""Caso de Uso: Envío de Sugerencias y Feedback Cualitativo (CU-11).

Anonimiza la IP con SHA-256 (PII-free) y persiste en sugerencias_feedback.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from db.database import SugerenciaFeedback


@dataclass
class FeedbackCreateDTO:
    categoria: str
    mensaje: str
    client_ip: str
    contacto_opcional: Optional[str] = None


class ManageFeedbackUseCase:
    VALID_CATEGORIES = {"Funcionalidad", "Nueva Tienda", "Error", "Otro"}

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Anonimiza la dirección IP aplicando SHA-256 (RNF-05)."""
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()

    def submit_feedback(self, dto: FeedbackCreateDTO) -> SugerenciaFeedback:
        categoria_limpia = dto.categoria.strip()
        if categoria_limpia not in self.VALID_CATEGORIES:
            categoria_limpia = "Otro"

        ip_hash = self.hash_ip(dto.client_ip)

        feedback = SugerenciaFeedback(
            categoria=categoria_limpia,
            mensaje=dto.mensaje.strip(),
            contacto_opcional=dto.contacto_opcional.strip() if dto.contacto_opcional else None,
            ip_hash=ip_hash,
        )
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return feedback

