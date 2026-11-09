from datetime import date, datetime, timezone
import math
from urllib.parse import quote_plus
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import distinct, func, not_, or_, literal, select, DateTime, String
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_db_session
from api.schemas import LatestStoreIncorporationResponse
from core.store_news_helper import contar_cafes_activos_tienda
from db.database import NovedadTienda, Producto, SucursalTienda, Tienda, Variante, _utcnow, engine_has_tienda_column
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
    id: Optional[int] = None
    nombre: str
    slug: Optional[str] = None
    telefono_whatsapp: Optional[str] = None
    url_base: Optional[str] = None
    url_catalogo: Optional[str] = None
    url_web: Optional[str] = None
    sitio_oficial: Optional[str] = None
    plataforma: Optional[str] = None
    direccion: Optional[str] = None
    descripcion: Optional[str] = None
    servicios: List[str] = []
    carta_comida_url: Optional[str] = None
    cantidad_productos: int
    comuna: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    distancia_km: Optional[float] = None
    logo_url: Optional[str] = None
    fecha_creacion: Optional[datetime] = None
    sucursales: List[StoreBranchPublicItem] = []


class StorePopularCoffeeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    marca: str
    formato_gramos: Optional[int] = 250
    precio_clp: Optional[int] = 0
    precio_por_kilo: Optional[float] = 0.0
    en_oferta: bool = False
    imagen_url: Optional[str] = None
    url_origen: Optional[str] = None
    origen: Optional[str] = None
    tipo_tueste: Optional[str] = None


class StoreNewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titulo: str
    descripcion: str
    link_url: Optional[str] = None
    imagen_url: Optional[str] = None
    categoria_tipo: Optional[str] = None
    fecha_creacion: datetime


class StoreCatalogProductItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    marca: str
    formato_gramos: Optional[int] = 250
    precio_clp: Optional[int] = 0
    precio_por_kilo: Optional[float] = 0.0
    en_oferta: bool = False
    imagen_url: Optional[str] = None
    url_origen: Optional[str] = None
    origen: Optional[str] = None
    tipo_tueste: Optional[str] = None


class StorePublicDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    slug: str
    url_base: Optional[str] = None
    sitio_oficial: Optional[str] = None
    logo_url: Optional[str] = None
    descripcion: Optional[str] = None
    comuna: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    telefono_whatsapp: Optional[str] = None
    instagram_url: Optional[str] = None
    envio_gratis_monto: Optional[int] = None
    retiro_en_tienda: bool = False
    dias_tueste: Optional[str] = None
    fecha_ultimo_tueste: Optional[date] = None
    servicios: List[str] = []
    carta_comida_url: Optional[str] = None
    carta_comida_tamano_bytes: Optional[int] = 0
    cantidad_productos: int = 0
    sucursales: List[StoreBranchPublicItem] = []
    cafes_populares: List[StorePopularCoffeeItem] = []
    novedades: List[StoreNewsItem] = []
    productos: List[StoreCatalogProductItem] = []


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
    sort_by: Literal["product_count_desc", "name_asc", "distance_asc", "created_desc"] = Query(
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

    bind = db_session.get_bind()
    has_logo = engine_has_tienda_column(bind, "logo_url")
    logo_col = Tienda.logo_url.label("logo_url") if has_logo else literal(None, type_=String).label("logo_url")

    has_whatsapp = engine_has_tienda_column(bind, "telefono_whatsapp")
    whatsapp_col = Tienda.telefono_whatsapp.label("telefono_whatsapp") if has_whatsapp else literal(None, type_=String).label("telefono_whatsapp")

    has_fecha = engine_has_tienda_column(bind, "fecha_creacion")
    fecha_col = Tienda.fecha_creacion.label("fecha_creacion") if has_fecha else literal(None, type_=DateTime).label("fecha_creacion")

    has_slug = engine_has_tienda_column(bind, "slug")
    slug_col = Tienda.slug.label("slug") if has_slug else literal(None, type_=String).label("slug")

    group_cols = [Tienda.id, Tienda.nombre, Tienda.url_base, Tienda.comuna, Tienda.latitud, Tienda.longitud]
    if has_fecha:
        group_cols.append(Tienda.fecha_creacion)
    if has_logo:
        group_cols.append(Tienda.logo_url)
    if has_whatsapp:
        group_cols.append(Tienda.telefono_whatsapp)
    if has_slug:
        group_cols.append(Tienda.slug)

    query = (
        db_session.query(
            Tienda.id.label("id"),
            Tienda.nombre.label("nombre"),
            Tienda.url_base.label("url_base"),
            Tienda.comuna.label("comuna"),
            Tienda.latitud.label("latitud"),
            Tienda.longitud.label("longitud"),
            whatsapp_col,
            logo_col,
            fecha_col,
            slug_col,
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
        .group_by(*group_cols)
    )

    if filter_comuna and not user_lat:
        query = query.filter(Tienda.comuna.ilike(f"%{filter_comuna}%"))

    if sort_by == "name_asc":
        query = query.order_by(Tienda.nombre.asc())
    elif sort_by == "created_desc" and has_fecha:
        query = query.order_by(Tienda.fecha_creacion.desc(), Tienda.nombre.asc())
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
            "id": getattr(row, "id", None),
            "nombre": row.nombre,
            "slug": getattr(row, "slug", None),
            "telefono_whatsapp": getattr(row, "telefono_whatsapp", None),
            "url_base": row.url_base,
            "url_catalogo": row.url_base,
            "url_web": official_site,
            "sitio_oficial": official_site,
            "cantidad_productos": row.cantidad_productos,
            "logo_url": getattr(row, "logo_url", None),
            "fecha_creacion": getattr(row, "fecha_creacion", None),
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



@tiendas_router.get(
    "/ultima-incorporada",
    response_model=Optional[LatestStoreIncorporationResponse],
    summary="Obtener la tostaduría más recientemente incorporada a Cafésitios",
    description="Devuelve la última tienda activa con productos disponibles en el catálogo, su conteo de cafés y novedad asociada.",
)
@router.get(
    "/latest",
    response_model=Optional[LatestStoreIncorporationResponse],
    include_in_schema=False,
)
def get_latest_store_incorporation(
    response: Response,
    db_session: Session = Depends(get_db_session),
) -> Optional[LatestStoreIncorporationResponse]:
    response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=300"

    tiendas_recientes = db_session.execute(
        select(Tienda)
        .where(Tienda.activo.is_(True))
        .order_by(Tienda.fecha_creacion.desc(), Tienda.id.desc())
        .limit(10)
    ).scalars().all()

    if not tiendas_recientes:
        return None

    selected_store: Optional[Tienda] = None
    cant_productos = 0
    for store in tiendas_recientes:
        total_cafes = contar_cafes_activos_tienda(store.id, db_session)
        if total_cafes > 0:
            selected_store = store
            cant_productos = total_cafes
            break

    if selected_store is None:
        selected_store = tiendas_recientes[0]
        cant_productos = contar_cafes_activos_tienda(selected_store.id, db_session)

    ahora = _utcnow()
    fecha_crea = selected_store.fecha_creacion or ahora
    if fecha_crea.tzinfo is not None and ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    elif fecha_crea.tzinfo is None and ahora.tzinfo is not None:
        fecha_crea = fecha_crea.replace(tzinfo=timezone.utc)

    dias_desde_incorporacion = max(0, (ahora - fecha_crea).days)
    es_reciente = dias_desde_incorporacion <= 30

    novedad = db_session.execute(
        select(NovedadTienda).where(
            NovedadTienda.tienda_id == selected_store.id,
            NovedadTienda.categoria_tipo == "nueva_tienda",
            NovedadTienda.activo.is_(True),
        )
    ).scalar_one_or_none()

    catalogo_url = f"/catalogo?tienda={quote_plus(selected_store.nombre.strip())}"

    return LatestStoreIncorporationResponse(
        id=selected_store.id,
        nombre=selected_store.nombre,
        logo_url=selected_store.logo_url,
        cantidad_productos=cant_productos,
        fecha_creacion=selected_store.fecha_creacion,
        dias_desde_incorporacion=dias_desde_incorporacion,
        es_reciente=es_reciente,
        catalogo_url=catalogo_url,
        novedad_id=novedad.id if novedad else None,
        titulo_novedad=novedad.titulo if novedad else f"¡Bienvenida {selected_store.nombre} a Cafésitios! 🎉",
        descripcion_novedad=novedad.descripcion if novedad else None,
    )


@tiendas_router.get(
    "/{slug_o_id}/detalle-publico",
    response_model=StorePublicDetailResponse,
    summary="Detalle público de la tostaduría, vitrina digital, servicios, menú y cafés destacados",
)
@tiendas_router.get("/{slug_o_id}", response_model=StorePublicDetailResponse, include_in_schema=False)
@router.get("/{slug_o_id}/public-detail", response_model=StorePublicDetailResponse, include_in_schema=False)
@router.get("/{slug_o_id}", response_model=StorePublicDetailResponse, include_in_schema=False)
def get_store_public_detail(
    slug_o_id: str,
    response: Response,
    db_session: Session = Depends(get_db_session),
) -> StorePublicDetailResponse:
    response.headers["Cache-Control"] = "public, s-maxage=60, stale-while-revalidate=300"

    clean_identifier = (slug_o_id or "").strip()
    if not clean_identifier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tienda no encontrada.")

    # 1. Buscar tienda por slug o id
    store = None
    if clean_identifier.isdigit():
        store = db_session.scalar(select(Tienda).where(Tienda.id == int(clean_identifier)))

    if not store:
        store = db_session.scalar(select(Tienda).where(Tienda.slug == clean_identifier.lower()))

    if not store:
        store = db_session.scalar(select(Tienda).where(Tienda.nombre.ilike(clean_identifier)))

    if not store or not store.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tienda no encontrada o inactiva.")

    # 2. Sucursales activas
    sucursales_orm = db_session.scalars(
        select(SucursalTienda)
        .where(SucursalTienda.tienda_id == store.id, SucursalTienda.activo.is_(True))
        .order_by(SucursalTienda.nombre.asc())
    ).all()
    sucursales_out = [
        StoreBranchPublicItem(
            id=b.id,
            nombre=b.nombre,
            direccion=b.direccion,
            comuna=b.comuna,
            region=b.region,
            latitud=float(b.latitud) if b.latitud is not None else None,
            longitud=float(b.longitud) if b.longitud is not None else None,
        )
        for b in sucursales_orm
    ]

    # 3. Novedades activas de la tienda
    novedades_orm = db_session.scalars(
        select(NovedadTienda)
        .where(NovedadTienda.tienda_id == store.id, NovedadTienda.activo.is_(True))
        .order_by(NovedadTienda.fecha_creacion.desc())
        .limit(6)
    ).all()
    novedades_out = [
        StoreNewsItem(
            id=n.id,
            titulo=n.titulo,
            descripcion=n.descripcion,
            link_url=n.link_url,
            imagen_url=n.imagen_url,
            categoria_tipo=n.categoria_tipo,
            fecha_creacion=n.fecha_creacion,
        )
        for n in novedades_orm
    ]

    # 4. Productos de café activos de la tienda
    non_coffee_clauses = [Producto.nombre.ilike(f"%{kw}%") for kw in NON_COFFEE_KEYWORDS_SQL]
    productos_query = (
        select(Producto)
        .where(
            Producto.tienda_id == store.id,
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            not_(or_(*non_coffee_clauses)),
        )
        .options(selectinload(Producto.variantes))
    )
    productos_orm = db_session.scalars(productos_query).all()

    productos_out = []
    for p in productos_orm:
        vars_disp = [v for v in (p.variantes or []) if bool(v.disponible)]
        if not vars_disp:
            continue
        v_main = min(vars_disp, key=lambda v: (v.precio_por_kilo or 99999999))
        productos_out.append(
            StoreCatalogProductItem(
                id=p.id,
                nombre=p.nombre,
                marca=store.nombre,
                formato_gramos=v_main.formato_gramos or 250,
                precio_clp=v_main.precio_clp or 0,
                precio_por_kilo=v_main.precio_por_kilo or 0.0,
                en_oferta=bool(v_main.en_oferta),
                imagen_url=getattr(p, "imagen", None),
                url_origen=getattr(p, "url_detalle", None),
                origen=getattr(p, "origen", None),
                tipo_tueste=getattr(p, "tipo_tueste", None),
            )
        )

    # 5. Cafés Populares (top 4 cafés ordenados por precio por kilo ascendente)
    cafes_populares = sorted(productos_out, key=lambda x: (x.precio_por_kilo or 999999))[:4]
    popular_items = [
        StorePopularCoffeeItem(
            id=cp.id,
            nombre=cp.nombre,
            marca=cp.marca,
            formato_gramos=cp.formato_gramos,
            precio_clp=cp.precio_clp,
            precio_por_kilo=cp.precio_por_kilo,
            en_oferta=cp.en_oferta,
            imagen_url=cp.imagen_url,
            url_origen=cp.url_origen,
            origen=cp.origen,
            tipo_tueste=cp.tipo_tueste,
        )
        for cp in cafes_populares
    ]

    official_site = extract_official_website(store.url_base)

    return StorePublicDetailResponse(
        id=store.id,
        nombre=store.nombre,
        slug=store.slug or f"tienda-{store.id}",
        url_base=store.url_base,
        sitio_oficial=official_site,
        logo_url=getattr(store, "logo_url", None),
        descripcion=getattr(store, "descripcion", None),
        comuna=store.comuna,
        direccion=getattr(store, "direccion", None),
        latitud=float(store.latitud) if store.latitud is not None else None,
        longitud=float(store.longitud) if store.longitud is not None else None,
        telefono_whatsapp=getattr(store, "telefono_whatsapp", None),
        instagram_url=getattr(store, "instagram_url", None),
        envio_gratis_monto=getattr(store, "envio_gratis_monto", None),
        retiro_en_tienda=bool(getattr(store, "retiro_en_tienda", False)),
        dias_tueste=getattr(store, "dias_tueste", None),
        fecha_ultimo_tueste=getattr(store, "fecha_ultimo_tueste", None),
        servicios=getattr(store, "servicios", None) or [],
        carta_comida_url=getattr(store, "carta_comida_url", None),
        carta_comida_tamano_bytes=getattr(store, "carta_comida_tamano_bytes", 0) or 0,
        cantidad_productos=len(productos_out),
        sucursales=sucursales_out,
        cafes_populares=popular_items,
        novedades=novedades_out,
        productos=productos_out,
    )
