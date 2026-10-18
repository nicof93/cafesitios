from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_db_session, require_local_admin
from api.stores import extract_official_website
from db.database import (
    DatabaseManager,
    Producto,
    Sincronizacion,
    SucursalTienda,
    Tienda,
    UsuarioTienda,
    Variante,
)
from domain.search_normalizer import (
    classify_product_category,
    detect_non_coffee_suspicion,
)
from scrapper.coffee_metadata import extract_coffee_characteristics
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver
from scrapper_application import sincronizar_tienda, sincronizar_multiples_tiendas

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administración Local"],
    dependencies=[Depends(require_local_admin)],
)


# --- DTOs de Tiendas y Sucursales ---
class BranchInput(BaseModel):
    id: Optional[int] = None
    nombre: str = Field(..., min_length=1, max_length=150)
    direccion: Optional[str] = Field(None, max_length=255)
    comuna: Optional[str] = Field(None, max_length=100)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True


class BranchOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    nombre: str
    direccion: Optional[str] = None
    comuna: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True


class StoreCreateUpdateRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    url_catalogo: str = Field(..., min_length=4, max_length=500)
    plataforma: str = Field("woocommerce", description="woocommerce, shopify o desconocida")
    direccion: Optional[str] = Field(None, max_length=255)
    comuna: Optional[str] = Field(None, max_length=100)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True
    email_administrador: Optional[str] = Field(
        None, max_length=150, description="Email del usuario administrador asignado a la tostaduría"
    )
    sucursales: List[BranchInput] = Field(default_factory=list)


class AdminStoreItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    url_catalogo: str
    url_base: str
    sitio_oficial: Optional[str] = None
    url_web: Optional[str] = None
    plataforma: str
    direccion: Optional[str] = None
    comuna: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True
    email_administrador: Optional[str] = None
    cantidad_productos_visibles: int = 0
    cantidad_productos_ocultos: int = 0
    cantidad_productos_sospechosos: int = 0
    ultima_sincronizacion: Optional[str] = None
    estado_sincronizacion: Optional[str] = None
    es_pendiente_sincronizacion: bool = True
    sucursales: List[BranchOutput] = Field(default_factory=list)


class AdminStoresListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_tiendas: int
    total_sincronizadas: int = 0
    total_pendientes: int = 0
    tiendas: List[AdminStoreItem]


class SingleStoreSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tienda_id: int
    nombre: str
    tienda_nombre: Optional[str] = None
    exito: bool
    estado: str = "exitoso"
    total_productos: int
    productos_encontrados: Optional[int] = None
    productos_nuevos: int
    productos_actualizados: int
    productos_eliminados: int = 0
    duracion_segundos: float
    error: Optional[str] = None
    mensaje: str


class BatchSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tipo_sincronizacion: str  # 'individual', 'pendientes', 'masiva'
    total_tiendas: int
    tiendas_exitosas: int
    tiendas_fallidas: int
    total_productos_sincronizados: int
    total_productos_nuevos: int
    total_productos_actualizados: int
    duracion_segundos: float
    mensaje: str
    detalles: List[SingleStoreSyncResponse]


class CatalogTestRequest(BaseModel):
    nombre: str = Field("Tienda de Prueba", min_length=1, max_length=120)
    url_catalogo: str = Field(..., min_length=4, max_length=500)
    plataforma: str = Field("auto", description="woocommerce, shopify, o auto")


class CatalogTestFirstProduct(BaseModel):
    id_externo: str
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    precio_clp: int = 0
    formato_gramos: int = 250
    precio_por_kilo: float = 0.0
    total_variantes: int = 0
    proceso: Optional[str] = None
    pais_origen: Optional[str] = None
    notas_cata: List[str] = Field(default_factory=list)
    es_sospechoso_no_cafe: bool = False
    motivo_sospecha: Optional[str] = None


class CatalogTestResponse(BaseModel):
    legible: bool
    plataforma_solicitada: str
    plataforma_detectada: Optional[str] = None
    url_probada: str
    total_productos_detectados: int = 0
    primer_producto: Optional[CatalogTestFirstProduct] = None
    mensaje: str
    error_detalle: Optional[str] = None


class StoresExportResponse(BaseModel):
    fecha_exportacion: str
    total_tiendas: int
    total_sucursales: int
    tiendas: List[Dict[str, Any]]
    sql_script: str


class StoresImportRequest(BaseModel):
    tiendas: List[StoreCreateUpdateRequest]


# --- DTOs de Moderación de Productos ---
class ModerationProductItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    tienda: str
    tienda_id: int
    url_detalle: str
    imagen: Optional[str] = None
    precio_clp: int = 0
    formato_gramos: int = 250
    precio_por_kilo: float = 0.0
    oculto_catalogo: bool = False
    es_sospechoso: bool = False
    motivo_sospecha: Optional[str] = None
    categoria_detectada: str = "cafe"


class StoreModerationCountItem(BaseModel):
    tienda: str
    tienda_id: int
    cantidad_productos_visibles: int
    cantidad_ocultos: int
    cantidad_sospechosos: int


class ModerationListResponse(BaseModel):
    total_sospechosos: int
    total_ocultos: int
    total_visibles_cafe: int
    conteo_por_tienda: List[StoreModerationCountItem]
    items: List[ModerationProductItem]


class VisibilityUpdateRequest(BaseModel):
    oculto_catalogo: bool


class BulkVisibilityUpdateRequest(BaseModel):
    product_ids: List[int]
    oculto_catalogo: bool


class VisibilityUpdateResponse(BaseModel):
    status: str
    updated_count: int
    oculto_catalogo: bool
    conteo_por_tienda: List[StoreModerationCountItem] = Field(default_factory=list)


def _normalize_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL del catálogo no puede estar vacía.",
        )
    if not re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    if not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL de catálogo inválida: {url}",
        )
    return cleaned


def _normalize_platform(plataforma: str) -> str:
    plat = (plataforma or "").strip().lower()
    if plat in ("woocommerce", "woo", "wp", "wordpress"):
        return "woocommerce"
    if plat in ("shopify",):
        return "shopify"
    if plat in ("jumpseller", "custom", "otra", "desconocida", "auto", ""):
        return "desconocida" if plat != "auto" else "auto"
    return plat


def _compute_store_moderation_counts(db_session: Session) -> List[StoreModerationCountItem]:
    stores = db_session.scalars(select(Tienda).order_by(Tienda.nombre.asc())).all()
    products = db_session.scalars(
        select(Producto).where(Producto.activo.is_(True))
    ).all()

    by_store: Dict[int, List[Producto]] = {s.id: [] for s in stores}
    for p in products:
        by_store.setdefault(p.tienda_id, []).append(p)

    counts: List[StoreModerationCountItem] = []
    for s in stores:
        prods = by_store.get(s.id, [])
        visibles = 0
        ocultos = 0
        sospechosos = 0
        for p in prods:
            reason = detect_non_coffee_suspicion(p.nombre, p.descripcion)
            is_non_coffee = classify_product_category(p.nombre) == "no_cafe" or reason is not None
            if bool(getattr(p, "oculto_catalogo", False)):
                ocultos += 1
            else:
                if is_non_coffee:
                    sospechosos += 1
                if classify_product_category(p.nombre) == "cafe":
                    visibles += 1
        counts.append(
            StoreModerationCountItem(
                tienda=s.nombre,
                tienda_id=s.id,
                cantidad_productos_visibles=visibles,
                cantidad_ocultos=ocultos,
                cantidad_sospechosos=sospechosos,
            )
        )
    return counts


def _sync_store_admin_user(
    db_session: Session, store_id: int, email: Optional[str]
) -> Optional[str]:
    """Crea, actualiza o consulta el usuario administrador vinculado a la tienda."""
    existing = db_session.scalars(
        select(UsuarioTienda).where(UsuarioTienda.tienda_id == store_id)
    ).first()

    if email is None:
        return existing.usuario_id if existing else None

    email_clean = email.strip().lower()
    if not email_clean:
        if existing:
            db_session.delete(existing)
            db_session.flush()
        return None

    if existing:
        existing.usuario_id = email_clean
        existing.rol = "STORE_ADMIN"
    else:
        new_user = UsuarioTienda(
            id=str(uuid.uuid4()),
            usuario_id=email_clean,
            tienda_id=store_id,
            rol="STORE_ADMIN",
        )
        db_session.add(new_user)
    db_session.flush()
    return email_clean


def _sql_literal(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Verificar estado de herramientas administrativas locales",
)
def get_admin_status() -> Dict[str, Any]:
    return {
        "enabled": True,
        "is_localhost": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/stores",
    response_model=AdminStoresListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todas las tiendas registradas y sus sucursales",
)
def list_admin_stores(db_session: Session = Depends(get_db_session)) -> AdminStoresListResponse:
    stores = (
        db_session.scalars(
            select(Tienda)
            .options(selectinload(Tienda.sucursales))
            .order_by(Tienda.nombre.asc())
        )
        .unique()
        .all()
    )
    counts_map = {
        c.tienda_id: c for c in _compute_store_moderation_counts(db_session)
    }

    # Mapa de administradores de tiendas vinculados
    user_stores = db_session.scalars(select(UsuarioTienda)).all()
    store_admin_map: Dict[int, str] = {u.tienda_id: u.usuario_id for u in user_stores}

    # Mapa de última sincronización por tienda
    latest_syncs = (
        db_session.scalars(
            select(Sincronizacion).order_by(
                Sincronizacion.tienda_id, Sincronizacion.fecha_inicio.desc()
            )
        ).all()
    )
    sync_map: Dict[int, Sincronizacion] = {}
    for sync in latest_syncs:
        if sync.tienda_id not in sync_map:
            sync_map[sync.tienda_id] = sync

    items: List[AdminStoreItem] = []
    for s in stores:
        cnt = counts_map.get(s.id)
        branches = [
            BranchOutput(
                id=b.id,
                tienda_id=b.tienda_id,
                nombre=b.nombre,
                direccion=b.direccion,
                comuna=b.comuna,
                latitud=b.latitud,
                longitud=b.longitud,
                activo=bool(b.activo),
            )
            for b in (getattr(s, "sucursales", None) or [])
        ]

        last_sync = sync_map.get(s.id)
        last_sync_time = (
            last_sync.fecha_inicio.isoformat()
            if (last_sync and last_sync.fecha_inicio)
            else None
        )
        last_sync_status = last_sync.resultado if last_sync else "nunca"
        total_prods = (cnt.cantidad_productos_visibles + cnt.cantidad_ocultos) if cnt else 0
        is_pending = (total_prods == 0) or (last_sync_status != "exitoso")

        items.append(
            AdminStoreItem(
                id=s.id,
                nombre=s.nombre,
                url_catalogo=s.url_base,
                url_base=s.url_base,
                sitio_oficial=extract_official_website(s.url_base),
                url_web=extract_official_website(s.url_base),
                plataforma=s.plataforma or "desconocida",
                direccion=getattr(s, "direccion", None),
                comuna=s.comuna,
                latitud=s.latitud,
                longitud=s.longitud,
                activo=bool(s.activo),
                email_administrador=store_admin_map.get(s.id),
                cantidad_productos_visibles=cnt.cantidad_productos_visibles if cnt else 0,
                cantidad_productos_ocultos=cnt.cantidad_ocultos if cnt else 0,
                cantidad_productos_sospechosos=cnt.cantidad_sospechosos if cnt else 0,
                ultima_sincronizacion=last_sync_time,
                estado_sincronizacion=last_sync_status,
                es_pendiente_sincronizacion=is_pending,
                sucursales=branches,
            )
        )

    total_pendientes = sum(1 for it in items if it.es_pendiente_sincronizacion and it.activo)
    total_sincronizadas = sum(1 for it in items if not it.es_pendiente_sincronizacion and it.activo)

    return AdminStoresListResponse(
        total_tiendas=len(items),
        total_sincronizadas=total_sincronizadas,
        total_pendientes=total_pendientes,
        tiendas=items,
    )


@router.post(
    "/stores",
    response_model=AdminStoreItem,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar o actualizar una tostaduría/tienda y sus sucursales",
)
def create_or_update_store(
    payload: StoreCreateUpdateRequest,
    db_session: Session = Depends(get_db_session),
) -> AdminStoreItem:
    nombre_limpio = payload.nombre.strip()
    url_normalizada = _normalize_url(payload.url_catalogo)
    plataforma_norm = _normalize_platform(payload.plataforma)
    if plataforma_norm == "auto":
        plataforma_norm = "desconocida"

    existing = db_session.scalars(
        select(Tienda)
        .options(selectinload(Tienda.sucursales))
        .where(func.lower(Tienda.nombre) == nombre_limpio.lower())
    ).first()

    if existing is None:
        store = Tienda(
            nombre=nombre_limpio,
            url_base=url_normalizada,
            plataforma=plataforma_norm,
            direccion=payload.direccion.strip() if payload.direccion else None,
            comuna=payload.comuna.strip() if payload.comuna else None,
            latitud=payload.latitud,
            longitud=payload.longitud,
            activo=payload.activo,
        )
        db_session.add(store)
        db_session.flush()
    else:
        store = existing
        store.nombre = nombre_limpio
        store.url_base = url_normalizada
        store.plataforma = plataforma_norm
        store.direccion = payload.direccion.strip() if payload.direccion else None
        store.comuna = payload.comuna.strip() if payload.comuna else None
        store.latitud = payload.latitud
        store.longitud = payload.longitud
        store.activo = payload.activo
        for old_b in list(store.sucursales):
            db_session.delete(old_b)
        db_session.flush()

    for b_in in payload.sucursales:
        if not b_in.nombre or not b_in.nombre.strip():
            continue
        branch = SucursalTienda(
            tienda_id=store.id,
            nombre=b_in.nombre.strip(),
            direccion=b_in.direccion.strip() if b_in.direccion else None,
            comuna=b_in.comuna.strip() if b_in.comuna else None,
            latitud=b_in.latitud,
            longitud=b_in.longitud,
            activo=b_in.activo,
        )
        db_session.add(branch)

    admin_email = _sync_store_admin_user(db_session, store.id, payload.email_administrador)

    db_session.commit()
    db_session.refresh(store)

    branches_out = [
        BranchOutput(
            id=b.id,
            tienda_id=b.tienda_id,
            nombre=b.nombre,
            direccion=b.direccion,
            comuna=b.comuna,
            latitud=b.latitud,
            longitud=b.longitud,
            activo=bool(b.activo),
        )
        for b in (store.sucursales or [])
    ]

    return AdminStoreItem(
        id=store.id,
        nombre=store.nombre,
        url_catalogo=store.url_base,
        url_base=store.url_base,
        sitio_oficial=extract_official_website(store.url_base),
        url_web=extract_official_website(store.url_base),
        plataforma=store.plataforma,
        direccion=getattr(store, "direccion", None),
        comuna=store.comuna,
        latitud=store.latitud,
        longitud=store.longitud,
        activo=bool(store.activo),
        email_administrador=admin_email,
        sucursales=branches_out,
    )


@router.put(
    "/stores/{store_id}",
    response_model=AdminStoreItem,
    status_code=status.HTTP_200_OK,
    summary="Actualizar una tienda existente y sus sucursales por ID",
)
def update_store_by_id(
    store_id: int,
    payload: StoreCreateUpdateRequest,
    db_session: Session = Depends(get_db_session),
) -> AdminStoreItem:
    store = db_session.scalars(
        select(Tienda)
        .options(selectinload(Tienda.sucursales))
        .where(Tienda.id == store_id)
    ).first()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada.",
        )

    plataforma_norm = _normalize_platform(payload.plataforma)
    if plataforma_norm == "auto":
        plataforma_norm = "desconocida"

    store.nombre = payload.nombre.strip()
    store.url_base = _normalize_url(payload.url_catalogo)
    store.plataforma = plataforma_norm
    store.direccion = payload.direccion.strip() if payload.direccion else None
    store.comuna = payload.comuna.strip() if payload.comuna else None
    store.latitud = payload.latitud
    store.longitud = payload.longitud
    store.activo = payload.activo

    for old_b in list(store.sucursales):
        db_session.delete(old_b)
    db_session.flush()

    for b_in in payload.sucursales:
        if not b_in.nombre or not b_in.nombre.strip():
            continue
        db_session.add(
            SucursalTienda(
                tienda_id=store.id,
                nombre=b_in.nombre.strip(),
                direccion=b_in.direccion.strip() if b_in.direccion else None,
                comuna=b_in.comuna.strip() if b_in.comuna else None,
                latitud=b_in.latitud,
                longitud=b_in.longitud,
                activo=b_in.activo,
            )
        )

    admin_email = _sync_store_admin_user(db_session, store.id, payload.email_administrador)

    db_session.commit()
    db_session.refresh(store)

    return AdminStoreItem(
        id=store.id,
        nombre=store.nombre,
        url_catalogo=store.url_base,
        url_base=store.url_base,
        sitio_oficial=extract_official_website(store.url_base),
        url_web=extract_official_website(store.url_base),
        plataforma=store.plataforma,
        direccion=getattr(store, "direccion", None),
        comuna=store.comuna,
        latitud=store.latitud,
        longitud=store.longitud,
        activo=bool(store.activo),
        email_administrador=admin_email,
        sucursales=[
            BranchOutput(
                id=b.id,
                tienda_id=b.tienda_id,
                nombre=b.nombre,
                direccion=b.direccion,
                comuna=b.comuna,
                latitud=b.latitud,
                longitud=b.longitud,
                activo=bool(b.activo),
            )
            for b in (store.sucursales or [])
        ],
    )


@router.post(
    "/stores/test-catalog",
    response_model=CatalogTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Probar si el catálogo ingresado es legible y obtener el primer producto con el driver",
)
@router.post(
    "/test-catalog",
    response_model=CatalogTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias para probar catálogo ingresado",
)
def test_store_catalog(payload: CatalogTestRequest) -> CatalogTestResponse:
    url_probada = _normalize_url(payload.url_catalogo)
    plataforma_solicitada = _normalize_platform(payload.plataforma)

    driver_map = {
        "woocommerce": ("woocommerce", WooCommerceDriver),
        "shopify": ("shopify", ShopifyDriver),
    }

    if plataforma_solicitada in driver_map:
        candidate_drivers = [driver_map[plataforma_solicitada]]
    else:
        candidate_drivers = [
            ("woocommerce", WooCommerceDriver),
            ("shopify", ShopifyDriver),
        ]

    errores: List[str] = []
    for plat_name, driver_cls in candidate_drivers:
        try:
            driver = driver_cls(nombre=payload.nombre, url_base=url_probada)
            try:
                productos = driver.consumir_productos(limit=3)
            except TypeError:
                productos = driver.consumir_productos()
            if productos and len(productos) > 0:
                first_raw = productos[0]
                variantes = first_raw.get("variantes") or []
                first_var = variantes[0] if variantes else {}
                precio_clp = int(first_var.get("precio_clp") or 0)
                formato_g = int(first_var.get("formato_gramos") or 250) or 250
                precio_kg = float(
                    first_var.get("precio_por_kilo")
                    or driver_cls.calcular_precio_por_kilo(precio_clp, formato_g)
                )

                caract = extract_coffee_characteristics(
                    first_raw.get("descripcion"),
                    title=first_raw.get("nombre"),
                )
                notas = first_raw.get("notas_cata") or caract.get("notas_cata") or []
                proceso = first_raw.get("proceso") or caract.get("proceso")
                pais = caract.get("pais_origen")
                suspicion = detect_non_coffee_suspicion(
                    first_raw.get("nombre"),
                    first_raw.get("descripcion"),
                )

                clean_notas: List[str] = []
                for n in notas[:6]:
                    if isinstance(n, dict):
                        val = n.get("nombre") or n.get("descriptor") or ""
                    else:
                        val = str(n)
                    val = val.strip(" .,;-")
                    if val and val.lower() not in [x.lower() for x in clean_notas]:
                        clean_notas.append(val)

                first_dto = CatalogTestFirstProduct(
                    id_externo=str(first_raw.get("id_externo") or "1"),
                    nombre=str(first_raw.get("nombre") or "Producto sin nombre"),
                    url_detalle=str(first_raw.get("url_detalle") or url_probada),
                    imagen=first_raw.get("imagen"),
                    precio_clp=precio_clp,
                    formato_gramos=formato_g,
                    precio_por_kilo=precio_kg,
                    total_variantes=len(variantes),
                    proceso=proceso,
                    pais_origen=pais,
                    notas_cata=clean_notas,
                    es_sospechoso_no_cafe=suspicion is not None,
                    motivo_sospecha=suspicion,
                )

                return CatalogTestResponse(
                    legible=True,
                    plataforma_solicitada=plataforma_solicitada,
                    plataforma_detectada=plat_name,
                    url_probada=url_probada,
                    total_productos_detectados=len(productos),
                    primer_producto=first_dto,
                    mensaje=(
                        f"Catálogo legible mediante driver {plat_name.upper()}. "
                        f"Se detectaron {len(productos)} productos. Primer producto: '{first_dto.nombre}'."
                    ),
                )
            else:
                errores.append(f"{driver_cls.__name__}: Catálogo vacío (0 productos devueltos).")
        except Exception as exc:
            errores.append(f"{driver_cls.__name__}: {str(exc)}")

    return CatalogTestResponse(
        legible=False,
        plataforma_solicitada=plataforma_solicitada,
        plataforma_detectada=None,
        url_probada=url_probada,
        total_productos_detectados=0,
        primer_producto=None,
        mensaje="No fue posible leer productos desde la URL ingresada con el driver seleccionado.",
        error_detalle=" | ".join(errores),
    )


@router.post(
    "/stores/{store_id}/sync",
    response_model=SingleStoreSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sincronizar el catálogo de una tostaduría específica",
)
def sync_single_store(
    store_id: int,
    db_session: Session = Depends(get_db_session),
) -> SingleStoreSyncResponse:
    store = db_session.scalars(select(Tienda).where(Tienda.id == store_id)).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tienda con ID {store_id} no encontrada.",
        )

    tienda_dict = {
        "id": store.id,
        "nombre": store.nombre,
        "url_base": store.url_base,
        "plataforma": store.plataforma or "desconocida",
    }
    db_manager = DatabaseManager()
    res = sincronizar_tienda(tienda_dict, db=db_manager)
    mensaje = (
        f"Sincronización exitosa: {res['total_productos']} productos sincronizados "
        f"({res['productos_nuevos']} nuevos, {res['productos_actualizados']} actualizados) en {res['duracion_segundos']}s."
        if res["exito"]
        else f"Error al sincronizar: {res['error']}"
    )
    return SingleStoreSyncResponse(
        tienda_id=res["tienda_id"],
        nombre=res["nombre"],
        tienda_nombre=res["nombre"],
        exito=res["exito"],
        estado="exitoso" if res["exito"] else "fallido",
        total_productos=res["total_productos"],
        productos_encontrados=res["total_productos"],
        productos_nuevos=res["productos_nuevos"],
        productos_actualizados=res["productos_actualizados"],
        productos_eliminados=res.get("productos_eliminados", 0),
        duracion_segundos=res["duracion_segundos"],
        error=res["error"],
        mensaje=mensaje,
    )


@router.post(
    "/sync/unsynced",
    response_model=BatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sincronizar únicamente las tiendas que no han sido sincronizadas o no tienen productos",
)
@router.post(
    "/stores/sync-unsynced",
    response_model=BatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias para sincronizar tiendas pendientes",
)
def sync_unsynced_stores(
    db_session: Session = Depends(get_db_session),
) -> BatchSyncResponse:
    db_manager = DatabaseManager()
    unsynced = db_manager.listar_tiendas_no_sincronizadas()
    if not unsynced:
        return BatchSyncResponse(
            tipo_sincronizacion="pendientes",
            total_tiendas=0,
            tiendas_exitosas=0,
            tiendas_fallidas=0,
            total_productos_sincronizados=0,
            total_productos_nuevos=0,
            total_productos_actualizados=0,
            duracion_segundos=0.0,
            mensaje="No hay tiendas pendientes de sincronización. Todas las tiendas activas ya cuentan con catálogo sincronizado.",
            detalles=[],
        )

    batch_res = sincronizar_multiples_tiendas(unsynced, db=db_manager, registrar_log_global=True)
    detalles_dto = [
        SingleStoreSyncResponse(
            tienda_id=d["tienda_id"],
            nombre=d["nombre"],
            tienda_nombre=d["nombre"],
            exito=d["exito"],
            estado="exitoso" if d["exito"] else "fallido",
            total_productos=d["total_productos"],
            productos_encontrados=d["total_productos"],
            productos_nuevos=d["productos_nuevos"],
            productos_actualizados=d["productos_actualizados"],
            productos_eliminados=d.get("productos_eliminados", 0),
            duracion_segundos=d["duracion_segundos"],
            error=d["error"],
            mensaje=f"{d['nombre']}: {'OK' if d['exito'] else d['error']}",
        )
        for d in batch_res["detalles"]
    ]
    mensaje = (
        f"Sincronización de pendientes finalizada: {batch_res['tiendas_exitosas']}/{batch_res['total_tiendas']} "
        f"tiendas procesadas correctamente ({batch_res['total_productos_sincronizados']} productos totales) en {batch_res['duracion_segundos']}s."
    )
    return BatchSyncResponse(
        tipo_sincronizacion="pendientes",
        total_tiendas=batch_res["total_tiendas"],
        tiendas_exitosas=batch_res["tiendas_exitosas"],
        tiendas_fallidas=batch_res["tiendas_fallidas"],
        total_productos_sincronizados=batch_res["total_productos_sincronizados"],
        total_productos_nuevos=batch_res["total_productos_nuevos"],
        total_productos_actualizados=batch_res["total_productos_actualizados"],
        duracion_segundos=batch_res["duracion_segundos"],
        mensaje=mensaje,
        detalles=detalles_dto,
    )


@router.post(
    "/sync/all",
    response_model=BatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sincronización masiva de todas las tiendas activas",
)
@router.post(
    "/stores/sync-all",
    response_model=BatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias para sincronización masiva",
)
def sync_all_stores(
    db_session: Session = Depends(get_db_session),
) -> BatchSyncResponse:
    db_manager = DatabaseManager()
    tiendas = db_manager.listar_tiendas_activas()
    if not tiendas:
        return BatchSyncResponse(
            tipo_sincronizacion="masiva",
            total_tiendas=0,
            tiendas_exitosas=0,
            tiendas_fallidas=0,
            total_productos_sincronizados=0,
            total_productos_nuevos=0,
            total_productos_actualizados=0,
            duracion_segundos=0.0,
            mensaje="No hay tiendas activas configuradas para sincronizar.",
            detalles=[],
        )

    batch_res = sincronizar_multiples_tiendas(tiendas, db=db_manager, registrar_log_global=True)
    detalles_dto = [
        SingleStoreSyncResponse(
            tienda_id=d["tienda_id"],
            nombre=d["nombre"],
            tienda_nombre=d["nombre"],
            exito=d["exito"],
            estado="exitoso" if d["exito"] else "fallido",
            total_productos=d["total_productos"],
            productos_encontrados=d["total_productos"],
            productos_nuevos=d["productos_nuevos"],
            productos_actualizados=d["productos_actualizados"],
            productos_eliminados=d.get("productos_eliminados", 0),
            duracion_segundos=d["duracion_segundos"],
            error=d["error"],
            mensaje=f"{d['nombre']}: {'OK' if d['exito'] else d['error']}",
        )
        for d in batch_res["detalles"]
    ]
    mensaje = (
        f"Sincronización masiva finalizada: {batch_res['tiendas_exitosas']}/{batch_res['total_tiendas']} "
        f"tiendas procesadas correctamente ({batch_res['total_productos_sincronizados']} productos totales) en {batch_res['duracion_segundos']}s."
    )
    return BatchSyncResponse(
        tipo_sincronizacion="masiva",
        total_tiendas=batch_res["total_tiendas"],
        tiendas_exitosas=batch_res["tiendas_exitosas"],
        tiendas_fallidas=batch_res["tiendas_fallidas"],
        total_productos_sincronizados=batch_res["total_productos_sincronizados"],
        total_productos_nuevos=batch_res["total_productos_nuevos"],
        total_productos_actualizados=batch_res["total_productos_actualizados"],
        duracion_segundos=batch_res["duracion_segundos"],
        mensaje=mensaje,
        detalles=detalles_dto,
    )


@router.get(
    "/stores/export",
    response_model=StoresExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Exportar tiendas y sucursales registradas para ambiente productivo (JSON + SQL)",
)
def export_stores_and_branches(
    db_session: Session = Depends(get_db_session),
) -> StoresExportResponse:
    stores = (
        db_session.scalars(
            select(Tienda)
            .options(selectinload(Tienda.sucursales))
            .order_by(Tienda.nombre.asc())
        )
        .unique()
        .all()
    )

    exported_stores: List[Dict[str, Any]] = []
    total_branches = 0
    sql_lines: List[str] = [
        "-- ============================================================================",
        "-- Exportación de Tostadurías y Sucursales - Cafesitios (Producción / Supabase)",
        f"-- Fecha de generación: {datetime.now(timezone.utc).isoformat()}",
        "-- ============================================================================",
        "BEGIN;",
        "",
    ]

    user_stores = db_session.scalars(select(UsuarioTienda)).all()
    store_admin_map: Dict[int, str] = {u.tienda_id: u.usuario_id for u in user_stores}

    for s in stores:
        branches_data = []
        for b in (getattr(s, "sucursales", None) or []):
            total_branches += 1
            branches_data.append(
                {
                    "nombre": b.nombre,
                    "direccion": b.direccion,
                    "comuna": b.comuna,
                    "latitud": b.latitud,
                    "longitud": b.longitud,
                    "activo": bool(b.activo),
                }
            )

        admin_email = store_admin_map.get(s.id)

        exported_stores.append(
            {
                "nombre": s.nombre,
                "url_catalogo": s.url_base,
                "url_base": s.url_base,
                "plataforma": s.plataforma or "desconocida",
                "direccion": getattr(s, "direccion", None),
                "comuna": s.comuna,
                "latitud": s.latitud,
                "longitud": s.longitud,
                "activo": bool(s.activo),
                "email_administrador": admin_email,
                "sucursales": branches_data,
            }
        )

        sql_lines.append(
            f"INSERT INTO tiendas (nombre, url_base, plataforma, direccion, comuna, latitud, longitud, activo) "
            f"VALUES ({_sql_literal(s.nombre)}, {_sql_literal(s.url_base)}, {_sql_literal(s.plataforma or 'desconocida')}, "
            f"{_sql_literal(getattr(s, 'direccion', None))}, {_sql_literal(s.comuna)}, "
            f"{_sql_literal(s.latitud)}, {_sql_literal(s.longitud)}, {_sql_literal(bool(s.activo))}) "
            f"ON CONFLICT (nombre) DO UPDATE SET "
            f"url_base = EXCLUDED.url_base, "
            f"plataforma = EXCLUDED.plataforma, "
            f"direccion = COALESCE(EXCLUDED.direccion, tiendas.direccion), "
            f"comuna = COALESCE(EXCLUDED.comuna, tiendas.comuna), "
            f"latitud = COALESCE(EXCLUDED.latitud, tiendas.latitud), "
            f"longitud = COALESCE(EXCLUDED.longitud, tiendas.longitud), "
            f"activo = EXCLUDED.activo;"
        )

        if admin_email:
            sql_lines.append(
                f"INSERT INTO usuarios_tienda (id, usuario_id, tienda_id, rol) "
                f"VALUES (gen_random_uuid(), {_sql_literal(admin_email)}, "
                f"(SELECT id FROM tiendas WHERE nombre = {_sql_literal(s.nombre)}), 'STORE_ADMIN') "
                f"ON CONFLICT (usuario_id, tienda_id) DO UPDATE SET rol = 'STORE_ADMIN';"
            )

        if branches_data:
            sql_lines.append(
                f"DELETE FROM sucursales_tienda WHERE tienda_id = (SELECT id FROM tiendas WHERE nombre = {_sql_literal(s.nombre)});"
            )
            for b in branches_data:
                sql_lines.append(
                    f"INSERT INTO sucursales_tienda (tienda_id, nombre, direccion, comuna, latitud, longitud, activo) "
                    f"VALUES ((SELECT id FROM tiendas WHERE nombre = {_sql_literal(s.nombre)}), "
                    f"{_sql_literal(b['nombre'])}, {_sql_literal(b['direccion'])}, {_sql_literal(b['comuna'])}, "
                    f"{_sql_literal(b['latitud'])}, {_sql_literal(b['longitud'])}, {_sql_literal(b['activo'])});"
                )
        sql_lines.append("")

    sql_lines.append("COMMIT;")

    return StoresExportResponse(
        fecha_exportacion=datetime.now(timezone.utc).isoformat(),
        total_tiendas=len(exported_stores),
        total_sucursales=total_branches,
        tiendas=exported_stores,
        sql_script="\n".join(sql_lines),
    )


@router.post(
    "/stores/import",
    status_code=status.HTTP_200_OK,
    summary="Importar lote de tiendas y sucursales desde JSON exportado",
)
def import_stores_and_branches(
    payload: StoresImportRequest,
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    imported = 0
    for store_req in payload.tiendas:
        create_or_update_store(store_req, db_session=db_session)
        imported += 1
    return {"status": "ok", "imported_stores": imported}


# --- Moderación de Productos No-Café y Visibilidad en Catálogo ---
@router.get(
    "/products/moderation",
    response_model=ModerationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar productos para moderación administrativa (sospechosos no-café, ocultos o todos)",
)
def list_moderation_products(
    mode: Literal["suspected", "hidden", "visible", "all"] = Query(
        "suspected",
        description="Filtro: 'suspected' (posibles no-café), 'hidden' (ocultos), 'visible' (visibles), 'all' (todos)",
    ),
    store_name: Optional[str] = Query(None, description="Filtrar por tienda"),
    q: Optional[str] = Query(None, description="Buscar por nombre de producto"),
    limit: int = Query(250, ge=1, le=1000),
    db_session: Session = Depends(get_db_session),
) -> ModerationListResponse:
    rows = (
        db_session.execute(
            select(Producto, Tienda)
            .join(Tienda, Producto.tienda_id == Tienda.id)
            .options(selectinload(Producto.variantes))
            .where(Producto.activo.is_(True))
            .order_by(Producto.id.desc())
        )
        .unique()
        .all()
    )

    total_sospechosos = 0
    total_ocultos = 0
    total_visibles_cafe = 0
    filtered_items: List[ModerationProductItem] = []

    q_lower = q.strip().lower() if q and q.strip() else None
    store_lower = store_name.strip().lower() if store_name and store_name.strip() else None

    for prod, tienda in rows:
        oculto = bool(getattr(prod, "oculto_catalogo", False))
        reason = detect_non_coffee_suspicion(prod.nombre, prod.descripcion)
        cat = classify_product_category(prod.nombre)
        es_sospechoso = reason is not None or cat == "no_cafe"

        if oculto:
            total_ocultos += 1
        else:
            if es_sospechoso:
                total_sospechosos += 1
            if cat == "cafe":
                total_visibles_cafe += 1

        if store_lower and store_lower not in (tienda.nombre or "").lower():
            continue
        if q_lower and q_lower not in (prod.nombre or "").lower():
            continue

        if mode == "suspected" and not (es_sospechoso and not oculto):
            continue
        if mode == "hidden" and not oculto:
            continue
        if mode == "visible" and oculto:
            continue

        variantes = prod.variantes or []
        avail_vars = [v for v in variantes if v.disponible] or variantes
        rep_var = min(avail_vars, key=lambda v: (int(v.precio_clp or 0), v.id)) if avail_vars else None

        precio_clp = int(rep_var.precio_clp or 0) if rep_var else 0
        formato_g = int(rep_var.formato_gramos or 250) if rep_var else 250
        precio_kg = float(rep_var.precio_por_kilo or 0.0) if rep_var else 0.0

        filtered_items.append(
            ModerationProductItem(
                id=prod.id,
                nombre=prod.nombre,
                tienda=tienda.nombre,
                tienda_id=tienda.id,
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                precio_clp=precio_clp,
                formato_gramos=formato_g,
                precio_por_kilo=precio_kg,
                oculto_catalogo=oculto,
                es_sospechoso=es_sospechoso,
                motivo_sospecha=reason or ("Detectado como accesorio / no-café" if cat == "no_cafe" else None),
                categoria_detectada="no_cafe" if es_sospechoso else "cafe",
            )
        )

    filtered_items.sort(
        key=lambda item: (
            0 if (item.es_sospechoso and not item.oculto_catalogo) else (1 if item.oculto_catalogo else 2),
            item.tienda.lower(),
            item.nombre.lower(),
        )
    )

    return ModerationListResponse(
        total_sospechosos=total_sospechosos,
        total_ocultos=total_ocultos,
        total_visibles_cafe=total_visibles_cafe,
        conteo_por_tienda=_compute_store_moderation_counts(db_session),
        items=filtered_items[:limit],
    )


@router.patch(
    "/products/{product_id}/visibility",
    response_model=VisibilityUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Ocultar o mostrar un producto del catálogo general",
)
def update_product_visibility(
    product_id: int,
    payload: VisibilityUpdateRequest,
    db_session: Session = Depends(get_db_session),
) -> VisibilityUpdateResponse:
    product = db_session.get(Producto, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    product.oculto_catalogo = bool(payload.oculto_catalogo)
    db_session.commit()

    return VisibilityUpdateResponse(
        status="ok",
        updated_count=1,
        oculto_catalogo=bool(product.oculto_catalogo),
        conteo_por_tienda=_compute_store_moderation_counts(db_session),
    )


@router.post(
    "/products/bulk-visibility",
    response_model=VisibilityUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Ocultar o restaurar múltiples productos en lote",
)
def bulk_update_product_visibility(
    payload: BulkVisibilityUpdateRequest,
    db_session: Session = Depends(get_db_session),
) -> VisibilityUpdateResponse:
    if not payload.product_ids:
        return VisibilityUpdateResponse(
            status="ok",
            updated_count=0,
            oculto_catalogo=payload.oculto_catalogo,
            conteo_por_tienda=_compute_store_moderation_counts(db_session),
        )

    products = db_session.scalars(
        select(Producto).where(Producto.id.in_(payload.product_ids))
    ).all()
    for p in products:
        p.oculto_catalogo = bool(payload.oculto_catalogo)
    db_session.commit()

    return VisibilityUpdateResponse(
        status="ok",
        updated_count=len(products),
        oculto_catalogo=bool(payload.oculto_catalogo),
        conteo_por_tienda=_compute_store_moderation_counts(db_session),
    )
