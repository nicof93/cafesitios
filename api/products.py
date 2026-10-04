import re
from html import escape
from html.parser import HTMLParser
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload

from api.dependencies import get_db_session
from api.schemas import (
    CheapestProductResponse,
    PaginatedProductsResponse,
    ProductDetailResponse,
    VariantResponse,
)
from application.get_cheapest_products import GetCheapestProductsUseCase
from db.database import Producto, ProductoNotaCata, Tienda, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository

router = APIRouter(prefix="/api/v1/products", tags=["Productos"])

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


@router.get(
    "/{product_id}/detail",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener el detalle de un producto y todas sus variantes",
    description="Retorna la ficha técnica detallada del café, notas de cata y el historial de precios por variante."
)
def get_product_detail(product_id: int, db_session: Session = Depends(get_db_session)) -> Dict[str, Any]:
    product = (
        db_session.query(Producto)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .options(
            joinedload(Producto.tienda),
            selectinload(Producto.variantes).selectinload(Variante.historial_precios),
            selectinload(Producto.notas_cata).joinedload(ProductoNotaCata.nota),
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
        "proceso": product.proceso,
        "pais_origen": product.pais_origen,
        "finca": product.finca,
        "variedad": product.variedad,
        "elevacion_min_msnm": product.elevacion_min_msnm,
        "elevacion_max_msnm": product.elevacion_max_msnm,
        "cosecha": product.cosecha,
        "fermentacion_tipo": product.fermentacion_tipo,
        "fermentacion_horas": float(product.fermentacion_horas) if product.fermentacion_horas is not None else None,
        "caracteristicas_fuente": product.caracteristicas_fuente or {},
        "notas_cata": [
            {
                "nombre": relation.nota.nombre,
                "clave_normalizada": relation.nota.clave_normalizada,
                "texto_origen": relation.texto_origen,
                "confianza": relation.confianza,
                "version_extractor": relation.version_extractor,
            }
            for relation in sorted(product.notas_cata, key=lambda relation: relation.nota.clave_normalizada)
        ],
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
    "",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener los cafés más baratos con filtros",
    description="Permite buscar y ordenar los cafés más económicos aplicando filtros por formato (gramos), tienda, precio o variedad."
)
@router.get(
    "/",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "/cheapest",
    response_model=PaginatedProductsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def get_cheapest_coffee_products(
    sort_by: Literal["kilo", "unit"] = Query(
        "kilo",
        description="Criterio de ordenamiento: 'kilo' ($/kg) o 'unit' (precio unitario en CLP)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Cantidad de productos a retornar (1-50)"),
    only_available: bool = Query(True, description="Filtrar solo productos que tengan stock disponible"),
    store_name: Optional[str] = Query(None, description="Filtrar por nombre de tienda (ej. 'Singular')"),
    store: Optional[str] = Query(None, description="Alias de tienda (ej. 'Singular')"),
    tienda: Optional[str] = Query(None, description="Alias en español para tienda"),
    min_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso mínimo en gramos (ej. 200)"),
    max_weight_g: Optional[int] = Query(None, ge=50, le=5000, description="Peso máximo en gramos (ej. 300)"),
    search_query: Optional[str] = Query(None, description="Búsqueda por texto en el nombre del café (ej. 'Geisha')"),
    min_price: Optional[int] = Query(None, ge=0, description="Precio unitario mínimo en CLP"),
    max_price: Optional[int] = Query(None, ge=0, description="Precio unitario máximo en CLP"),
    process: Optional[str] = Query(None, min_length=1, max_length=255, description="Filtrar por proceso de beneficio"),
    country: Optional[str] = Query(None, min_length=1, max_length=255, description="Filtrar por país de origen"),
    pais_origen: Optional[str] = Query(None, min_length=1, max_length=255, description="Alias en español para país de origen"),
    variety: Optional[str] = Query(None, min_length=1, max_length=255, description="Filtrar por variedad del café"),
    variedad: Optional[str] = Query(None, min_length=1, max_length=255, description="Alias en español para variedad"),
    notes: Optional[str] = Query(None, min_length=1, max_length=255, description="Filtrar por nota de cata"),
    notas_cata: Optional[str] = Query(None, min_length=1, max_length=255, description="Alias en español para nota de cata"),
    tasting_notes: Optional[str] = Query(None, min_length=1, max_length=255, description="Alias de nota de cata"),
    db_session: Session = Depends(get_db_session)
) -> PaginatedProductsResponse:
    try:
        if store_name is None:
            store_name = store or tienda
        if country is None:
            country = pais_origen
        if variety is None:
            variety = variedad
        if notes is None:
            notes = notas_cata or tasting_notes

        import api.router
        repo_cls = getattr(api.router, "PostgresCoffeeRepository", PostgresCoffeeRepository)
        repository = repo_cls(session=db_session)
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
            max_price=max_price,
            process=process,
            country=country,
            variety=variety,
            tasting_notes=notes,
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
                process=process,
                country=country,
                variety=variety,
                tasting_notes=notes,
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
