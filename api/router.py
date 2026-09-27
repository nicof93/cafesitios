from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Literal, Optional

from db.database import DatabaseManager
from infrastructure.postgres_repository import PostgresCoffeeRepository
from application.get_cheapest_products import GetCheapestProductsUseCase
from api.schemas import PaginatedProductsResponse, CheapestProductResponse, VariantResponse

router = APIRouter(prefix="/api/v1/products", tags=["Productos"])

def get_db_session():
    db = DatabaseManager()
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()

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
            total_items=len(items_dto),
            criterio_orden=f"Precio por {'kilo ($/kg)' if sort_by == 'kilo' else 'unidad ($ CLP)'}",
            data=items_dto
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la consulta: {str(e)}"
        )
