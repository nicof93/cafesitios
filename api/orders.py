"""Módulo de Pedidos e Intermediación de Ventas (WhatsApp Leads).

Permite registrar el intento de pedido por WhatsApp antes de redirigir al usuario,
brindando trazabilidad de pedidos para las tostadurías asociadas.
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from db.database import PedidoWhatsApp, Tienda, _utcnow

router = APIRouter(prefix="/api/v1/orders", tags=["Pedidos"])
pedidos_router = APIRouter(prefix="/api/v1/pedidos", tags=["Pedidos"])

# Rate limiting en memoria (10 intentos por minuto por IP)
_whatsapp_rate_limit: Dict[str, List[float]] = defaultdict(list)
WHATSAPP_WINDOW_SECONDS = 60
WHATSAPP_MAX_REQUESTS = 10


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _check_whatsapp_rate_limit(client_ip: str) -> None:
    now = time.time()
    timestamps = _whatsapp_rate_limit[client_ip]
    _whatsapp_rate_limit[client_ip] = [t for t in timestamps if now - t < WHATSAPP_WINDOW_SECONDS]
    if len(_whatsapp_rate_limit[client_ip]) >= WHATSAPP_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Has alcanzado el límite de intentos de pedidos por minuto (máximo 10). Por favor espera un momento.",
        )
    _whatsapp_rate_limit[client_ip].append(now)


class WhatsAppOrderItemInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    producto_id: Optional[Union[int, str]] = None
    nombre: str = Field(..., min_length=1, max_length=255)
    formato: Optional[str] = Field(default="250g", max_length=50)
    molienda: Optional[str] = Field(default=None, max_length=50)
    cantidad: int = Field(default=1, ge=1, le=100)
    precio_unitario_clp: int = Field(default=0, ge=0)


class WhatsAppLeadCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tienda_id: Union[int, str]
    dispositivo_uuid: str = Field(..., min_length=1, max_length=100)
    monto_total_clp: int = Field(..., ge=0)
    items: List[WhatsAppOrderItemInput] = Field(..., min_length=1)


class WhatsAppLeadResponse(BaseModel):
    id: int
    exito: bool = True
    mensaje: str = "Intento de pedido vía WhatsApp registrado exitosamente."


def _handle_create_whatsapp_lead(
    payload: WhatsAppLeadCreateRequest,
    request: Request,
    db_session: Session,
) -> WhatsAppLeadResponse:
    client_ip = _get_client_ip(request)
    _check_whatsapp_rate_limit(client_ip)

    # Validar tienda_id (acepta int o str convertible)
    raw_id = payload.tienda_id
    tienda_id_int: Optional[int] = None
    if isinstance(raw_id, int):
        tienda_id_int = raw_id
    elif isinstance(raw_id, str):
        if raw_id.strip().isdigit():
            tienda_id_int = int(raw_id.strip())
        else:
            # Buscar por nombre o url_base si no es número
            tienda_obj = db_session.query(Tienda).filter(
                (Tienda.nombre.ilike(raw_id.strip())) | (Tienda.url_base.ilike(f"%{raw_id.strip()}%"))
            ).first()
            if tienda_obj:
                tienda_id_int = tienda_obj.id

    if tienda_id_int is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identificador de tostaduría no válido o no encontrado.",
        )

    tienda = db_session.query(Tienda).filter(Tienda.id == tienda_id_int, Tienda.activo.is_(True)).first()
    if not tienda:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tostaduría no encontrada o inactiva en el catálogo.",
        )

    items_data = [item.model_dump() for item in payload.items]

    pedido = PedidoWhatsApp(
        tienda_id=tienda.id,
        dispositivo_uuid=payload.dispositivo_uuid.strip(),
        monto_total_clp=int(payload.monto_total_clp),
        items=items_data,
        estado="ENVIADO",
        ip_origen=client_ip,
        fecha_creacion=_utcnow(),
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)

    return WhatsAppLeadResponse(
        id=pedido.id,
        exito=True,
        mensaje="Intento de pedido vía WhatsApp registrado exitosamente.",
    )


@pedidos_router.post(
    "/whatsapp-lead",
    response_model=WhatsAppLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar intento de pedido por WhatsApp (Lead)",
    description="Registra el lead de compra antes de redirigir a la API de WhatsApp de la tostaduría.",
)
def create_whatsapp_lead_es(
    payload: WhatsAppLeadCreateRequest,
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> WhatsAppLeadResponse:
    return _handle_create_whatsapp_lead(payload, request, db_session)


@router.post(
    "/whatsapp-lead",
    response_model=WhatsAppLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar intento de pedido por WhatsApp (Lead)",
    description="Alias en inglés para registro de lead WhatsApp.",
    include_in_schema=False,
)
def create_whatsapp_lead_en(
    payload: WhatsAppLeadCreateRequest,
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> WhatsAppLeadResponse:
    return _handle_create_whatsapp_lead(payload, request, db_session)
