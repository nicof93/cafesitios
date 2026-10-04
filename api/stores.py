import math
from typing import Any, Dict, List, Literal
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from db.database import Producto, Tienda, Variante

router = APIRouter(prefix="/api/v1/stores", tags=["Tiendas"])


class StoreSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str
    cantidad_productos: int


class StoresSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: List[StoreSummaryItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@router.get(
    "",
    response_model=StoresSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener tiendas con su cantidad de productos disponibles",
    description="Devuelve el ranking de tiendas según la cantidad de productos disponibles, con paginación y orden configurable."
)
@router.get(
    "/",
    response_model=StoresSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def get_stores_summary(
    page: int = Query(1, ge=1, description="Número de página (empezando en 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de tiendas por página"),
    sort_by: Literal["product_count_desc", "name_asc"] = Query(
        "product_count_desc",
        description="Orden de resultados: 'product_count_desc' o 'name_asc'"
    ),
    db_session: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    if not hasattr(db_session, "query"):
        return {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total_items": 0,
            "total_pages": 0,
        }

    query = (
        db_session.query(
            Tienda.nombre.label("nombre"),
            func.count(distinct(Producto.id)).label("cantidad_productos")
        )
        .join(Producto, Producto.tienda_id == Tienda.id)
        .join(Variante, Variante.producto_id == Producto.id)
        .filter(
            Tienda.activo.is_(True),
            Producto.activo.is_(True),
            Variante.disponible == True,
        )
        .group_by(Tienda.id, Tienda.nombre)
    )

    if sort_by == "name_asc":
        query = query.order_by(Tienda.nombre.asc())
    else:
        query = query.order_by(func.count(distinct(Producto.id)).desc(), Tienda.nombre.asc())

    total_items = query.count()
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "nombre": row.nombre,
                "cantidad_productos": row.cantidad_productos,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
    }
