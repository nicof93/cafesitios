import math
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session, joinedload
from typing import Literal, Optional

from db.database import DatabaseManager, EstadoSincronizacion, Tienda, Producto, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository
from application.get_cheapest_products import GetCheapestProductsUseCase
from api.schemas import (
    PaginatedProductsResponse,
    CheapestProductResponse,
    VariantResponse,
    ProductDetailResponse,
)

router = APIRouter(prefix="/api/v1/products", tags=["Productos"])
stores_router = APIRouter(prefix="/api/v1", tags=["Tiendas"])

def get_db_session():
    db = DatabaseManager()
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()

@stores_router.get(
    "/sync/last",
    status_code=status.HTTP_200_OK,
    summary="Obtener la fecha de la última sincronización exitosa"
)
def get_last_sync(db_session: Session = Depends(get_db_session)):
    if not hasattr(db_session, "get"):
        return {"last_sync": None}

    estado = db_session.get(EstadoSincronizacion, 1)
    return {"last_sync": estado.ultima_ejecucion if estado else None}

@stores_router.get(
    "/stores",
    status_code=status.HTTP_200_OK,
    summary="Obtener tiendas con su cantidad de productos disponibles",
    description="Devuelve el ranking de tiendas según la cantidad de productos disponibles, con paginación y orden configurable."
)
def get_stores_summary(
    page: int = Query(1, ge=1, description="Número de página (empezando en 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de tiendas por página"),
    sort_by: Literal["product_count_desc", "name_asc"] = Query(
        "product_count_desc",
        description="Orden de resultados: 'product_count_desc' o 'name_asc'"
    ),
    db_session: Session = Depends(get_db_session)
):
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

@router.get(
    "/{product_id}/detail",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener el detalle de un producto y todas sus variantes"
)
def get_product_detail(product_id: int, db_session: Session = Depends(get_db_session)):
    product = (
        db_session.query(Producto)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .options(joinedload(Producto.tienda), joinedload(Producto.variantes))
        .filter(
            Producto.id == product_id,
            Producto.activo.is_(True),
            Tienda.activo.is_(True),
        )
        .first()
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )

    return {
        "id": product.id,
        "tienda": product.tienda.nombre,
        "tienda_url": product.tienda.url_base,
        "nombre": product.nombre,
        "descripcion": product.descripcion,
        "url_detalle": product.url_detalle,
        "imagen": product.imagen,
        "fecha_actualizacion": product.fecha_actualizacion,
        "variantes": [
            {
                "id_externo": variant.id_variante_externo,
                "opcion": variant.opcion,
                "formato_gramos": variant.formato_gramos,
                "precio_clp": variant.precio_clp,
                "precio_original_clp": variant.precio_original_clp,
                "en_oferta": variant.en_oferta,
                "descuento_porcentaje": variant.descuento_porcentaje,
                "precio_por_kilo": float(variant.precio_por_kilo),
                "disponible": variant.disponible,
                "fecha_actualizacion": variant.fecha_actualizacion,
            }
            for variant in product.variantes
        ],
    }

@router.get(
    "/cheapest", 
    response_model=PaginatedProductsResponse, 
    status_code=status.HTTP_200_OK,
    summary="Obtener los cafés más baratos con filtros",
    description="Permite buscar y ordenar los cafés más económicos aplicando filtros por formato (gramos), tienda, precio o variedad."
)
def get_cheapest_coffee_products(
    sort_by: Literal["kilo", "unit"] = Query(
        "kilo", 
        description="Criterio de ordenamiento: 'kilo' ($/kg) o 'unit' (precio unitario en CLP)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Cantidad de productos a retornar (1-50)"),
    only_available: bool = Query(True, description="Filtrar solo productos que tengan stock disponible"),
    store_name: Optional[str] = Query(None, description="Filtrar por nombre de tienda (ej. 'Singular')"),
    min_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso mínimo en gramos (ej. 200)"),
    max_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso máximo en gramos (ej. 300)"),
    search_query: Optional[str] = Query(None, description="Búsqueda por texto en el nombre del café (ej. 'Geisha')"),
    min_price: Optional[int] = Query(None, ge=0, description="Precio unitario mínimo en CLP"),
    max_price: Optional[int] = Query(None, ge=0, description="Precio unitario máximo en CLP"),
    db_session: Session = Depends(get_db_session)
):
    try:
        repository = PostgresCoffeeRepository(session=db_session)
        use_case = GetCheapestProductsUseCase(repository=repository)

        productos_dominio = use_case.execute(
            sort_by=sort_by, 
            limit=limit, 
            only_available=only_available,
            store_name=store_name,
            min_weight_g=min_weight_g,
            max_weight_g=max_weight_g,
            search_query=search_query,
            min_price=min_price,
            max_price=max_price
        )

        total_items = len(productos_dominio)
        if hasattr(repository, "count_cheapest_products"):
            total_items = repository.count_cheapest_products(
                sort_by=sort_by,
                only_available=only_available,
                store_name=store_name,
                min_weight_g=min_weight_g,
                max_weight_g=max_weight_g,
                search_query=search_query,
                min_price=min_price,
                max_price=max_price,
            )

        items_dto = [
            CheapestProductResponse(
                id=prod.id,
                tienda=prod.tienda,
                nombre=prod.nombre,
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                variante=VariantResponse(
                    id_externo=prod.variante_mas_barata.id_externo,
                    opcion=prod.variante_mas_barata.opcion,
                    formato_gramos=prod.variante_mas_barata.formato_gramos,
                    precio_clp=prod.variante_mas_barata.precio_clp,
                    precio_original_clp=prod.variante_mas_barata.precio_original_clp,
                    en_oferta=prod.variante_mas_barata.en_oferta,
                    descuento_porcentaje=prod.variante_mas_barata.descuento_porcentaje,
                    precio_por_kilo=prod.variante_mas_barata.precio_por_kilo,
                    disponible=prod.variante_mas_barata.disponible
                )
            ) for prod in productos_dominio
        ]

        return PaginatedProductsResponse(
            total_items=total_items,
            criterio_orden=f"Precio por {'kilo ($/kg)' if sort_by == 'kilo' else 'unidad ($ CLP)'}",
            data=items_dto
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la consulta: {str(e)}"
        )
