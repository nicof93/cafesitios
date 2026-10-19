"""Router de Telemetría y Registro de Eventos/Clics (Sección 5 y 7).

Registra interacciones del usuario (outbound_click, compare_view, share, etc.)
anonimizando la IP mediante SHA-256.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from api.schemas import TelemetryEventRequest, TelemetryEventResponse
from application.manage_telemetry import ManageTelemetryUseCase

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetría"])
telemetria_router = APIRouter(prefix="/api/v1/telemetria", tags=["Telemetría"])


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@telemetria_router.post(
    "/evento",
    response_model=TelemetryEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar evento de telemetría o clic saliente",
    description="Almacena el evento anonimizando la dirección IP (cero captura de PII)."
)
@telemetria_router.post("/event", response_model=TelemetryEventResponse, include_in_schema=False)
@router.post(
    "/evento",
    response_model=TelemetryEventResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
@router.post(
    "/event",
    response_model=TelemetryEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar evento de telemetría o clic saliente",
    description="Almacena el evento anonimizando la dirección IP (cero captura de PII)."
)
def record_event(
    payload: TelemetryEventRequest,
    request: Request,
    db_session: Session = Depends(get_db_session)
) -> TelemetryEventResponse:
    client_ip = _get_client_ip(request)
    use_case = ManageTelemetryUseCase(session=db_session)
    interaccion = use_case.record_click_event(
        tipo_evento=payload.tipo_evento,
        client_ip=client_ip,
        producto_id=payload.producto_id,
        variante_id=payload.variante_id,
        metadata_evento=payload.metadata_evento,
    )
    return TelemetryEventResponse(
        status="ok",
        event_id=interaccion.id,
    )

