import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from api.dependencies import get_db_session
from api.schemas import NovedadItemResponse, PaginatedNovedadesResponse
from db.config import settings
from db.database import NovedadTienda, Tienda

router = APIRouter(prefix="/api/v1/novedades", tags=["Novedades"])
news_router = APIRouter(prefix="/api/v1/news", tags=["Novedades"])
posts_router = APIRouter(prefix="/api/v1/posts", tags=["Novedades"])


def _check_feature_enabled() -> None:
    if not settings.is_store_posts_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sección de novedades y anuncios se encuentra deshabilitada temporalmente."
        )


def _to_dto(item: NovedadTienda) -> NovedadItemResponse:
    return NovedadItemResponse(
        id=item.id,
        tienda_id=item.tienda_id,
        tienda_nombre=item.tienda.nombre if item.tienda else "Tostaduría",
        tienda_logo_url=getattr(item.tienda, "logo_url", None) if item.tienda else None,
        tienda_url_base=item.tienda.url_base if item.tienda else None,
        titulo=item.titulo,
        descripcion=item.descripcion,
        link_url=item.link_url,
        imagen_url=item.imagen_url,
        categoria_tipo=item.categoria_tipo,
        fecha_inicio=item.fecha_inicio,
        fecha_fin=item.fecha_fin,
        activo=bool(item.activo),
        creado_por_rol=item.creado_por_rol or "STORE_ADMIN",
        fecha_creacion=item.fecha_creacion,
        fecha_actualizacion=item.fecha_actualizacion,
    )


@router.get(
    "",
    response_model=PaginatedNovedadesResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar novedades y promociones de tostadurías (Público)",
    description="Feed público de anuncios, ferias, ventas y promociones publicadas por las tostadurías asociadas."
)
@router.get("/", response_model=PaginatedNovedadesResponse, include_in_schema=False)
@news_router.get("", response_model=PaginatedNovedadesResponse, include_in_schema=False)
@posts_router.get("", response_model=PaginatedNovedadesResponse, include_in_schema=False)
def list_novedades(
    response: Response,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(12, ge=1, le=50, description="Cantidad de novedades por página"),
    tienda_id: Optional[int] = Query(None, description="Filtrar por ID de tostaduría"),
    tipo: Optional[str] = Query(None, description="Filtrar por categoría (promocion, evento, feria, lanzamiento, etc.)"),
    db_session: Session = Depends(get_db_session)
) -> PaginatedNovedadesResponse:
    _check_feature_enabled()

    # Encabezado de caché para Edge / CDN
    response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=300"

    base_query = (
        select(NovedadTienda)
        .join(Tienda, NovedadTienda.tienda_id == Tienda.id)
        .where(
            NovedadTienda.activo.is_(True),
            Tienda.activo.is_(True),
        )
    )

    if tienda_id is not None:
        base_query = base_query.where(NovedadTienda.tienda_id == tienda_id)

    if tipo and tipo.strip():
        clean_tipo = tipo.strip().lower()
        if clean_tipo in ("sin_categoria", "ninguna", "none", "null", "vacio"):
            base_query = base_query.where(NovedadTienda.categoria_tipo.is_(None))
        else:
            base_query = base_query.where(NovedadTienda.categoria_tipo == clean_tipo)

    # Contar total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_count = db_session.execute(count_stmt).scalar() or 0

    offset = (page - 1) * limit
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    has_more = page < total_pages

    items_stmt = (
        base_query
        .options(joinedload(NovedadTienda.tienda))
        .order_by(NovedadTienda.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
    )
    db_items = db_session.execute(items_stmt).scalars().all()

    return PaginatedNovedadesResponse(
        total=total_count,
        page=page,
        limit=limit,
        total_paginas=total_pages,
        has_more=has_more,
        items=[_to_dto(item) for item in db_items]
    )


@router.get(
    "/{novedad_id}",
    response_model=NovedadItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalle de novedad o anuncio comercial",
    description="Retorna la información completa de una publicación activa."
)
@news_router.get("/{novedad_id}", response_model=NovedadItemResponse, include_in_schema=False)
@posts_router.get("/{novedad_id}", response_model=NovedadItemResponse, include_in_schema=False)
def get_novedad_detail(
    novedad_id: int,
    response: Response,
    db_session: Session = Depends(get_db_session)
) -> NovedadItemResponse:
    _check_feature_enabled()
    response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=300"

    stmt = (
        select(NovedadTienda)
        .join(Tienda, NovedadTienda.tienda_id == Tienda.id)
        .options(joinedload(NovedadTienda.tienda))
        .where(
            NovedadTienda.id == novedad_id,
            NovedadTienda.activo.is_(True),
            Tienda.activo.is_(True),
        )
    )
    item = db_session.execute(stmt).scalars().first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La publicación solicitada no existe o no se encuentra disponible."
        )

    return _to_dto(item)

