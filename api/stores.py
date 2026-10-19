import math
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import distinct, func, not_, or_
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from db.database import Producto, SucursalTienda, Tienda, Variante
from domain.search_normalizer import NON_COFFEE_KEYWORDS_SQL

router = APIRouter(prefix="/api/v1/stores", tags=["Tiendas"])
tiendas_router = APIRouter(prefix="/api/v1/tiendas", tags=["Tiendas"])

# Coordenadas de referencia para comunas y ciudades de Chile ($0 USD geocoding)
COMUNA_COORDINATES: Dict[str, tuple] = {
    "santiago": (-33.4489, -70.6693),
    "providencia": (-33.4314, -70.6093),
    "las condes": (-33.4117, -70.5808),
    "nunoa": (-33.4569, -70.5975),
    "ñuñoa": (-33.4569, -70.5975),
    "la reina": (-33.4475, -70.5367),
    "vitacura": (-33.3833, -70.5833),
    "vina del mar": (-33.0245, -71.5518),
    "viña del mar": (-33.0245, -71.5518),
    "valparaiso": (-33.0472, -71.6127),
    "valparaíso": (-33.0472, -71.6127),
    "concepcion": (-36.8201, -73.0444),
    "concepción": (-36.8201, -73.0444),
    "puerto varas": (-41.3195, -72.9854),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia Haversine en kilómetros."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)


from urllib.parse import urlparse

def extract_official_website(url: Optional[str]) -> Optional[str]:
    """Extrae el sitio web oficial cortado estrictamente en el dominio raíz (protocolo + host, sin rutas)."""
    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


class StoreBranchPublicItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    direccion: Optional[str] = None
    comuna: Optional[str] = None
    region: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class StoreSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str
    url_base: Optional[str] = None
    url_catalogo: Optional[str] = None
    url_web: Optional[str] = None
    sitio_oficial: Optional[str] = None
    plataforma: Optional[str] = None
    direccion: Optional[str] = None
    cantidad_productos: int
    comuna: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    distancia_km: Optional[float] = None
    sucursales: List[StoreBranchPublicItem] = []


class StoresSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: List[StoreSummaryItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    ubicacion_referencia: Optional[str] = None


@tiendas_router.get(
    "",
    response_model=StoresSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener tiendas con cantidad de productos y cercanía física (CU-05)",
    description="Devuelve el catálogo de tiendas con orden por productos, nombre o cercanía geográfica pasiva."
)
@tiendas_router.get(
    "/",
    response_model=StoresSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
@router.get(
    "",
    response_model=StoresSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener tiendas con cantidad de productos y cercanía física (CU-05)",
    description="Devuelve el catálogo de tiendas con orden por productos, nombre o cercanía geográfica pasiva."
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
    sort_by: Literal["product_count_desc", "name_asc", "distance_asc"] = Query(
        "product_count_desc",
        description="Orden de resultados: 'product_count_desc', 'name_asc', o 'distance_asc'"
    ),
    db_session: Session = Depends(get_db_session),
    comuna: Optional[str] = Query(None, description="Filtrar o centrar por comuna (ej. 'Providencia')"),
    lat: Optional[float] = Query(None, description="Latitud del usuario"),
    lon: Optional[float] = Query(None, description="Longitud del usuario"),
    x_vercel_ip_city: Optional[str] = Header(None, alias="x-vercel-ip-city"),
) -> Dict[str, Any]:
    if not hasattr(db_session, "query"):
        return {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total_items": 0,
            "total_pages": 0,
            "ubicacion_referencia": None,
        }

    # Resolver coordenadas del usuario (CU-05: Nivel 1 Vercel Header, Nivel 2 Selector manual)
    user_lat = lat if isinstance(lat, (int, float)) else None
    user_lon = lon if isinstance(lon, (int, float)) else None
    filter_comuna = comuna if isinstance(comuna, str) else None
    header_city = x_vercel_ip_city if isinstance(x_vercel_ip_city, str) else None
    ref_name = None

    if user_lat is None or user_lon is None:
        target_loc = (filter_comuna or header_city or "").strip().lower()
        if target_loc in COMUNA_COORDINATES:
            user_lat, user_lon = COMUNA_COORDINATES[target_loc]
            ref_name = target_loc.title()

    non_coffee_clauses = [Producto.nombre.ilike(f"%{kw}%") for kw in NON_COFFEE_KEYWORDS_SQL]

    query = (
        db_session.query(
            Tienda.nombre.label("nombre"),
            Tienda.url_base.label("url_base"),
            Tienda.comuna.label("comuna"),
            Tienda.latitud.label("latitud"),
            Tienda.longitud.label("longitud"),
            func.count(distinct(Producto.id)).label("cantidad_productos")
        )
        .join(Producto, Producto.tienda_id == Tienda.id)
        .join(Variante, Variante.producto_id == Producto.id)
        .filter(
            Tienda.activo.is_(True),
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            not_(or_(*non_coffee_clauses)),
            Variante.disponible == True,
        )
        .group_by(Tienda.id, Tienda.nombre, Tienda.url_base, Tienda.comuna, Tienda.latitud, Tienda.longitud)
    )

    if filter_comuna and not user_lat:
        query = query.filter(Tienda.comuna.ilike(f"%{filter_comuna}%"))

    if sort_by == "name_asc":
        query = query.order_by(Tienda.nombre.asc())
    elif sort_by == "product_count_desc":
        query = query.order_by(func.count(distinct(Producto.id)).desc(), Tienda.nombre.asc())

    all_rows = query.all()

    # Cargar sucursales activas si la sesión lo soporta
    sucursales_por_nombre: Dict[str, List[Dict[str, Any]]] = {}
    try:
        branch_rows = (
            db_session.query(SucursalTienda, Tienda.nombre)
            .join(Tienda, SucursalTienda.tienda_id == Tienda.id)
            .filter(SucursalTienda.activo.is_(True), Tienda.activo.is_(True))
            .all()
        )
        for br, store_name in branch_rows:
            if not hasattr(br, "nombre") or not isinstance(store_name, str):
                continue
            sucursales_por_nombre.setdefault(store_name, []).append({
                "id": br.id,
                "nombre": br.nombre,
                "direccion": br.direccion,
                "comuna": br.comuna,
                "region": br.region,
                "latitud": float(br.latitud) if br.latitud is not None else None,
                "longitud": float(br.longitud) if br.longitud is not None else None,
            })
    except Exception:
        pass

    items = []
    for row in all_rows:
        dist_km = None
        if user_lat is not None and user_lon is not None and row.latitud is not None and row.longitud is not None:
            dist_km = haversine_distance(user_lat, user_lon, float(row.latitud), float(row.longitud))

        official_site = extract_official_website(row.url_base)
        item_dict: Dict[str, Any] = {
            "nombre": row.nombre,
            "url_base": row.url_base,
            "url_catalogo": row.url_base,
            "url_web": official_site,
            "sitio_oficial": official_site,
            "cantidad_productos": row.cantidad_productos,
            "sucursales": sucursales_por_nombre.get(row.nombre, []),
        }
        if row.comuna:
            item_dict["comuna"] = row.comuna
        if row.latitud is not None:
            item_dict["latitud"] = float(row.latitud)
        if row.longitud is not None:
            item_dict["longitud"] = float(row.longitud)
        if dist_km is not None:
            item_dict["distancia_km"] = dist_km

        items.append(item_dict)

    if sort_by == "distance_asc":
        items.sort(key=lambda x: (x.get("distancia_km") is None, x.get("distancia_km", 999999), -x["cantidad_productos"]))

    total_items = len(items)
    total_pages = math.ceil(total_items / page_size) if total_items else 0
    offset = (page - 1) * page_size
    paginated_items = items[offset:offset + page_size]

    return {
        "items": paginated_items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "ubicacion_referencia": ref_name,
    }

