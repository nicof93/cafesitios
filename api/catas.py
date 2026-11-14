"""Endpoints públicos para Catas y Paneles Sensoriales (SCA).

Permite a catadores, baristas y clientes acceder a la hoja de cata pública
mediante un token temporal sin necesidad de iniciar sesión, y enviar
evaluaciones inmutables.
"""
from datetime import datetime
from typing import Any, Dict, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from api.dependencies import get_db_session
from api.schemas import (
    CataPublicMetadataResponse,
    CataRespuestaPublicaRequest,
)
from db.database import Cata, CataRespuesta

logger = logging.getLogger(__name__)

# Enrutador canónico en español y alias para compatibilidad
catas_router = APIRouter(prefix="/api/v1/catas", tags=["Catas & Paneles Sensoriales"])
cuppings_router = APIRouter(prefix="/api/v1/cuppings", tags=["Catas & Paneles Sensoriales"])


def _obtener_cata_por_token(token: str, db_session: Session) -> Cata:
    token_limpio = (token or "").strip()
    if not token_limpio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token de cata no especificado."
        )

    cata = (
        db_session.query(Cata)
        .options(
            joinedload(Cata.tienda),
            joinedload(Cata.producto),
            joinedload(Cata.respuestas)
        )
        .filter(Cata.token_publico == token_limpio)
        .first()
    )

    if not cata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El panel sensorial solicitado no existe o el enlace es inválido."
        )
    return cata


@catas_router.get(
    "/publica/{token}",
    response_model=CataPublicMetadataResponse,
    summary="Obtener metadatos de la hoja de cata pública",
    description="Permite al catador ver información del panel, tostaduría, café a evaluar y estado de vigencia."
)
@catas_router.get("/{token}", response_model=CataPublicMetadataResponse, include_in_schema=False)
@cuppings_router.get("/public/{token}", response_model=CataPublicMetadataResponse, include_in_schema=False)
@cuppings_router.get("/{token}", response_model=CataPublicMetadataResponse, include_in_schema=False)
def get_cata_publica_metadata(
    token: str,
    db_session: Session = Depends(get_db_session)
) -> CataPublicMetadataResponse:
    cata = _obtener_cata_por_token(token, db_session)
    ahora = datetime.utcnow()
    esta_vigente = (cata.estado == 'activa') and (cata.fecha_expiracion > ahora)

    return CataPublicMetadataResponse(
        nombre=cata.nombre,
        descripcion=cata.descripcion,
        tienda_nombre=cata.tienda.nombre if cata.tienda else "Tostaduría",
        producto_nombre=cata.producto.nombre if cata.producto else None,
        fecha_expiracion=cata.fecha_expiracion,
        esta_vigente=esta_vigente,
        valores_iniciales_75=cata.valores_iniciales_75,
        total_respuestas_hasta_ahora=len(cata.respuestas or [])
    )


@catas_router.post(
    "/publica/{token}/respuestas",
    status_code=status.HTTP_201_CREATED,
    summary="Enviar evaluación individual de cata",
    description="Recibe la evaluación inmutable de un catador con los 10 atributos SCA, notas y observaciones."
)
@catas_router.post("/{token}/respuestas", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@cuppings_router.post("/public/{token}/responses", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@cuppings_router.post("/{token}/responses", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def submit_cata_publica_respuesta(
    token: str,
    payload: CataRespuestaPublicaRequest,
    db_session: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    cata = _obtener_cata_por_token(token, db_session)
    ahora = datetime.utcnow()

    if cata.estado != 'activa' or cata.fecha_expiracion <= ahora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El panel sensorial ha finalizado o su enlace ha expirado. Ya no se aceptan nuevas respuestas."
        )

    # Cálculo determinista del puntaje total SCA (suma de 10 atributos - defectos)
    suma_atributos = (
        payload.fragancia_aroma +
        payload.sabor +
        payload.sabor_residual +
        payload.acidez +
        payload.cuerpo +
        payload.uniformidad +
        payload.balance +
        payload.taza_limpia +
        payload.dulzor +
        payload.puntaje_general
    )
    puntaje_total = round(max(0.0, min(100.0, suma_atributos - payload.defectos)), 2)

    # Limpieza de notas sensoriales identificadas
    notas_limpias: List[str] = []
    if payload.notas_identificadas:
        for nota in payload.notas_identificadas:
            n = (nota or "").strip().lower()
            if n and len(n) <= 50 and n not in notas_limpias:
                notas_limpias.append(n)
        notas_limpias = notas_limpias[:20]

    nueva_respuesta = CataRespuesta(
        cata_id=cata.id,
        nombre_catador=payload.nombre_catador.strip(),
        fragancia_aroma=round(payload.fragancia_aroma, 2),
        sabor=round(payload.sabor, 2),
        sabor_residual=round(payload.sabor_residual, 2),
        acidez=round(payload.acidez, 2),
        cuerpo=round(payload.cuerpo, 2),
        uniformidad=round(payload.uniformidad, 2),
        balance=round(payload.balance, 2),
        taza_limpia=round(payload.taza_limpia, 2),
        dulzor=round(payload.dulzor, 2),
        puntaje_general=round(payload.puntaje_general, 2),
        defectos=round(payload.defectos, 2),
        puntaje_total=puntaje_total,
        notas_identificadas=notas_limpias,
        observaciones=payload.observaciones.strip() if payload.observaciones else None,
        fecha_creacion=ahora
    )

    db_session.add(nueva_respuesta)
    db_session.commit()
    db_session.refresh(nueva_respuesta)

    logger.info(
        f"Registrada evaluación de cata ID={cata.id} ('{cata.nombre}') por '{nueva_respuesta.nombre_catador}' con {puntaje_total} pts."
    )

    return {
        "status": "success",
        "mensaje": "¡Evaluación de cata registrada exitosamente!",
        "respuesta_id": nueva_respuesta.id,
        "nombre_catador": nueva_respuesta.nombre_catador,
        "puntaje_total": puntaje_total
    }
