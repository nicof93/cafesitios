"""Router de Sugerencias y Feedback Cualitativo (CU-11).

Incluye:
- Rate Limiting estricto (2 envíos por hora por IP)
- Honeypot Anti-Bot con campo 'website_hp'
- Anonimización de la dirección IP con SHA-256
"""

import time
from collections import defaultdict
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from api.schemas import FeedbackCreateRequest, FeedbackResponse
from application.manage_feedback import FeedbackCreateDTO, ManageFeedbackUseCase

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])
sugerencias_router = APIRouter(prefix="/api/v1/sugerencias", tags=["Sugerencias"])

_feedback_rate_limit: Dict[str, List[float]] = defaultdict(list)
FEEDBACK_WINDOW_SECONDS = 3600  # 1 hora
FEEDBACK_MAX_REQUESTS = 2       # 2 envíos por hora


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _check_feedback_rate_limit(client_ip: str) -> None:
    now = time.time()
    timestamps = _feedback_rate_limit[client_ip]
    _feedback_rate_limit[client_ip] = [t for t in timestamps if now - t < FEEDBACK_WINDOW_SECONDS]
    if len(_feedback_rate_limit[client_ip]) >= FEEDBACK_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Has alcanzado el límite de sugerencias (máximo 2 por hora). ¡Gracias por tu aporte!"
        )
    _feedback_rate_limit[client_ip].append(now)


@sugerencias_router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar sugerencia o reporte de feedback (CU-11)",
    description="Permite a los usuarios enviar retroalimentación cualitativa de forma segura y anónima."
)
@sugerencias_router.post("/", response_model=FeedbackResponse, include_in_schema=False)
@sugerencias_router.post("/sugerencia", response_model=FeedbackResponse, include_in_schema=False)
@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar sugerencia o reporte de feedback (CU-11)",
    description="Permite a los usuarios enviar retroalimentación cualitativa de forma segura y anónima."
)
@router.post("/", response_model=FeedbackResponse, include_in_schema=False)
@router.post("/sugerencia", response_model=FeedbackResponse, include_in_schema=False)
def submit_feedback(
    payload: FeedbackCreateRequest,
    request: Request,
    db_session: Session = Depends(get_db_session)
) -> FeedbackResponse:
    # 1. Honeypot check
    if payload.website_hp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Petición rechazada por detección de bot."
        )

    # 2. Rate limiting (2 por hora por IP)
    client_ip = _get_client_ip(request)
    _check_feedback_rate_limit(client_ip)

    # 3. Persistencia con IP anonimizada (SHA-256)
    use_case = ManageFeedbackUseCase(session=db_session)
    use_case.submit_feedback(
        FeedbackCreateDTO(
            categoria=payload.categoria,
            mensaje=payload.mensaje,
            client_ip=client_ip,
            contacto_opcional=payload.contacto_opcional,
        )
    )

    return FeedbackResponse(
        status="ok",
        message="¡Muchas gracias por tu sugerencia! La revisaremos con una taza de café en mano."
    )

