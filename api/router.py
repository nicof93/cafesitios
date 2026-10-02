import math
import re
from html import escape
from html.parser import HTMLParser
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Literal, Optional
from urllib.parse import urlsplit

from db.database import DatabaseManager, EstadoSincronizacion, HistorialPrecio, Tienda, Producto, Variante
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

_DESCRIPTION_TAGS = {
    'a', 'b', 'blockquote', 'br', 'caption', 'div', 'em', 'figcaption', 'figure',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p',
    'span', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul',
}
_DESCRIPTION_VOID_TAGS = {'br', 'hr', 'img'}
_DESCRIPTION_DROP_TAGS = {'embed', 'iframe', 'math', 'object', 'script', 'style', 'svg'}


def _safe_description_url(value: str) -> Optional[str]:
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() in {'http', 'https', 'mailto'}:
        return value
    if parsed.scheme or value.startswith(('//', '\\\\')):
        return None
    return value


def _safe_description_style(value: str) -> str:
    declarations = []
    for declaration in value.split(';'):
        name, separator, setting = declaration.partition(':')
        if not separator:
            continue
        name = name.strip().lower()
        setting = setting.strip().lower()
        if name == 'text-align' and setting in {'left', 'right', 'center', 'justify'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'font-weight' and setting in {'normal', 'bold', '400', '500', '600', '700', '800', '900'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'font-style' and setting in {'normal', 'italic', 'oblique'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'text-decoration' and setting in {'none', 'underline', 'line-through'}:
            declarations.append(f'{name}: {setting}')
        elif name == 'color' and re.fullmatch(r'#[0-9a-f]{3,8}|[a-z]{3,20}', setting):
            declarations.append(f'{name}: {setting}')
    return '; '.join(declarations)


class _DescriptionSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.open_tags = []
        self.suppressed_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.suppressed_depth:
            if tag in _DESCRIPTION_DROP_TAGS:
                self.suppressed_depth += 1
            return
        if tag in _DESCRIPTION_DROP_TAGS:
            self.suppressed_depth = 1
            return
        if tag not in _DESCRIPTION_TAGS:
            return

        safe_attrs = []
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            href = _safe_description_url(attrs['href'])
            if href:
                safe_attrs.extend([('href', href), ('rel', 'noopener noreferrer')])
                if attrs.get('title'):
                    safe_attrs.append(('title', attrs['title']))
        elif tag == 'img':
            src = _safe_description_url(attrs.get('src', ''))
            if not src:
                return
            safe_attrs.append(('src', src))
            for name in ('alt', 'title'):
                if attrs.get(name):
                    safe_attrs.append((name, attrs[name]))
        if attrs.get('style'):
            style = _safe_description_style(attrs['style'])
            if style:
                safe_attrs.append(('style', style))

        rendered_attrs = ''.join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        self.output.append(f'<{tag}{rendered_attrs}>')
        if tag not in _DESCRIPTION_VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.suppressed_depth:
            if tag in _DESCRIPTION_DROP_TAGS:
                self.suppressed_depth -= 1
            return
        if tag not in self.open_tags:
            return
        position = len(self.open_tags) - 1 - self.open_tags[::-1].index(tag)
        for open_tag in reversed(self.open_tags[position:]):
            self.output.append(f'</{open_tag}>')
        del self.open_tags[position:]

    def handle_data(self, data):
        if not self.suppressed_depth:
            self.output.append(escape(data))

    def handle_comment(self, data):
        pass

    def get_html(self, source: Optional[str]) -> str:
        self.feed(source or '')
        self.close()
        for tag in reversed(self.open_tags):
            self.output.append(f'</{tag}>')
        self.open_tags.clear()
        return ''.join(self.output)

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
        .options(
            joinedload(Producto.tienda),
            selectinload(Producto.variantes).selectinload(Variante.historial_precios),
        )
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
        "descripcion": _DescriptionSanitizer().get_html(product.descripcion),
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
                "historial_precios": [
                    {
                        "fecha_registro": history.fecha_registro,
                        "precio_clp": history.precio_clp,
                        "precio_por_kilo": float(history.precio_por_kilo),
                    }
                    for history in sorted(
                        variant.historial_precios,
                        key=lambda history: history.fecha_registro,
                    )
                ],
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
