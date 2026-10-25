from core.storage_manager import get_tienda_storage_info
from datetime import datetime, timezone, timedelta
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
import base64
import os
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, desc, text
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_db_session
from core.security_store_admin import (
    StoreAdminContext,
    anti_brute_force,
    create_store_admin_token,
    get_client_ip,
    get_current_store_admin,
    hash_store_password,
    log_store_action,
    verify_anti_bot_token,
    verify_store_password,
)
from db.database import (
    AuditoriaAccionesTienda,
    DatabaseManager,
    HistorialPrecio,
    InteraccionClic,
    NotaCata,
    PedidoWhatsApp,
    Producto,
    ProductoNotaCata,
    Receta,
    Sincronizacion,
    SincronizacionLog,
    SucursalTienda,
    Tienda,
    TiendaCatalogo,
    UsuarioTienda,
    Variante,
)
from scrapper_application import sincronizar_tienda
from api.admin import CatalogTestRequest, CatalogTestResponse, test_store_catalog


router = APIRouter(prefix="/api/v1/admin/tienda", tags=["Admin Tienda Multi-Inquilino"])


# --- DTOs Pydantic v2 ---
class TopCoffeeInterestItem(BaseModel):
    producto_id: int
    nombre: str
    total_clics: int


class StoreTelemetrySummaryResponse(BaseModel):
    tienda_id: int
    clics_salientes_totales: int
    total_favoritos_guardados: int
    apariciones_comparador: int
    top_cafes: List[TopCoffeeInterestItem] = Field(default_factory=list)


# --- DTOs de Catálogos y Sucursales para Tienda (Fase 2) ---
class StoreCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    url_catalogo: str
    etiqueta: Optional[str] = None
    activa: bool = True
    creado_en: Optional[datetime] = None


class StoreCatalogCreateRequest(BaseModel):
    url_catalogo: str = Field(..., min_length=4, max_length=500)
    etiqueta: Optional[str] = Field(None, max_length=100)


class StoreProfileUpdateRequest(BaseModel):
    direccion: Optional[str] = Field(None, max_length=255)
    comuna: Optional[str] = Field(None, max_length=100)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    telefono_whatsapp: Optional[str] = Field(None, max_length=50)
    envio_gratis_monto: Optional[int] = None
    retiro_en_tienda: Optional[bool] = None
    dias_tueste: Optional[str] = Field(None, max_length=100)
    fecha_ultimo_tueste: Optional[str] = None


class StoreBranchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    nombre: str
    direccion: Optional[str] = None
    comuna: Optional[str] = None
    region: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True


class StoreBranchCreateUpdateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    direccion: Optional[str] = Field(None, max_length=255)
    comuna: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True

class StoreAdminLoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str = Field(..., min_length=3, max_length=150)
    password: Optional[str] = None
    usuario_id: Optional[str] = None
    oauth_provider: Optional[str] = None  # 'google', 'github', 'supabase'
    oauth_token: Optional[str] = None
    turnstile_token: Optional[str] = None


class StoreAdminLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    usuario_id: str
    tienda_id: int
    tienda_nombre: str
    rol: str
    debe_cambiar_password: bool = False
    scraping_activo: bool = True


class StoreChangePasswordRequest(BaseModel):
    password_actual: Optional[str] = None
    password_nuevo: str = Field(..., min_length=6, max_length=100)


class StoreAdminProfileResponse(BaseModel):
    usuario_id: str
    tienda_id: int
    tienda_nombre: str
    tienda_url: str
    plataforma: str
    activo: bool
    scraping_activo: bool = True
    limite_almacenamiento_mb: int = 250
    almacenamiento_usado_mb: float = 0.0
    almacenamiento_porcentaje: float = 0.0
    rol: str
    ultima_sincronizacion: Optional[str] = None
    estado_sincronizacion: Optional[str] = None
    total_productos: int = 0
    cooldown_sync_segundos: int = 0
    logo_url: Optional[str] = None
    telefono_whatsapp: Optional[str] = None
    envio_gratis_monto: Optional[int] = None
    retiro_en_tienda: bool = False
    dias_tueste: Optional[str] = None
    fecha_ultimo_tueste: Optional[str] = None


class StoreInconsistencyItem(BaseModel):
    producto_id: int
    nombre: str
    tipo_inconsistencia: str
    detalle: str
    url_detalle: Optional[str] = None


class StoreInconsistenciesResponse(BaseModel):
    total_inconsistencias: int
    inconsistencias: List[StoreInconsistencyItem]


class BenchmarkOriginItem(BaseModel):
    origen: str
    precio_kilo_promedio_tienda: float
    precio_kilo_promedio_mercado: float
    diferencia_porcentaje: float


class StoreBenchmarkResponse(BaseModel):
    precio_kilo_promedio_tienda: float
    precio_kilo_promedio_mercado: float
    diferencia_porcentaje: float
    posicion_mercado: str
    desglose_por_origen: List[BenchmarkOriginItem]


class StoreUnmetDemandResponse(BaseModel):
    origenes_mas_buscados: List[Dict[str, Any]]
    oportunidades_catalogo: List[str]


class StoreWhatsAppConfigRequest(BaseModel):
    telefono_whatsapp: Optional[str] = Field(default=None, max_length=50)


class StoreWhatsAppOrderOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    dispositivo_uuid: str
    monto_total_clp: int
    items: List[Dict[str, Any]]
    estado: str
    fecha_creacion: datetime


class StoreWhatsAppMetricsOutput(BaseModel):
    ventas_whatsapp_30d: int
    total_pedidos_30d: int
    incremento_estimado_clp: int
    texto_proyeccion: str


class StoreProductVariantInput(BaseModel):
    id_variante_externo: Optional[str] = None
    opcion: str = "250g"
    formato_gramos: int = 250
    precio_clp: int = Field(..., gt=0)
    precio_original_clp: Optional[int] = None
    en_oferta: bool = False
    disponible: bool = True


class StoreProductInput(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255)
    url_detalle: Optional[str] = None
    imagen: Optional[str] = None
    descripcion: Optional[str] = None
    origen: Optional[str] = None
    finca: Optional[str] = None
    variedad: Optional[str] = None
    proceso: Optional[str] = None
    tueste: Optional[str] = None
    sca_score: Optional[float] = None
    notas_cata: List[str] = Field(default_factory=list)
    activo: bool = True
    oculto_catalogo: bool = False
    variantes: List[StoreProductVariantInput] = Field(default_factory=list)


class StoreProductVariantOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    id_variante_externo: str
    opcion: str
    formato_gramos: int
    precio_clp: int
    precio_original_clp: int
    en_oferta: bool
    descuento_porcentaje: int
    precio_por_kilo: float
    disponible: bool


class StoreProductOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    descripcion: Optional[str] = None
    origen: Optional[str] = None
    finca: Optional[str] = None
    variedad: Optional[str] = None
    proceso: Optional[str] = None
    tueste: Optional[str] = None
    sca_score: Optional[float] = None
    notas_cata: List[str] = Field(default_factory=list)
    activo: bool
    oculto_catalogo: bool
    es_manual: bool = True
    variantes: List[StoreProductVariantOutput] = Field(default_factory=list)



class StoreProductImageUploadRequest(BaseModel):
    imagen_base64: str = Field(..., description="Imagen en base64 con o sin prefijo data:image/...")
    nombre_archivo: Optional[str] = Field(None, max_length=150)


class StoreProductImageUploadResponse(BaseModel):
    exito: bool
    imagen_url: str
    mensaje: str
    mb_usados: float
    limite_mb: int
    porcentaje_usado: float

class StoreProductsListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_paginas: int
    productos: List[StoreProductOutput]


class StoreSyncActionResponse(BaseModel):
    exito: bool
    tienda_id: int
    tienda_nombre: str
    total_productos: int
    productos_nuevos: int
    productos_actualizados: int
    duracion_segundos: float
    error: Optional[str] = None
    mensaje: str
    cooldown_activo_segundos: int


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda_id: int
    usuario_id: str
    accion: str
    entidad: str
    entidad_id: Optional[int] = None
    valores_previos: Optional[Dict[str, Any]] = None
    valores_nuevos: Optional[Dict[str, Any]] = None
    ip_origen: Optional[str] = None
    fecha_registro: datetime


class AuditLogsListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    registros: List[AuditLogItem]


class StoreRecipeInput(BaseModel):
    producto_id: int
    nombre_receta: str = Field(..., min_length=2, max_length=150)
    metodo: str = Field(..., min_length=2, max_length=100)
    dosis_cafe_g: float = Field(..., gt=0)
    agua_ml: float = Field(..., gt=0)
    ratio: Optional[str] = Field(None, max_length=20)
    molino_usado: Optional[str] = Field(None, max_length=100)
    grosor_molienda: Optional[str] = Field(None, max_length=50)
    temperatura_c: Optional[int] = Field(None, ge=40, le=100)
    tiempo_total_s: Optional[int] = Field(None, ge=10, le=1800)
    notas_catado: Optional[str] = None
    es_borrador: bool = False
    pasos: Optional[List[str]] = None


class StoreRecipeOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: Optional[int]
    producto_nombre: Optional[str] = None
    tienda_id: Optional[int]
    nombre_receta: str
    metodo: str
    dosis_cafe_g: float
    agua_ml: float
    ratio: Optional[str] = None
    molino_usado: Optional[str] = None
    grosor_molienda: Optional[str] = None
    temperatura_c: Optional[int] = None
    tiempo_total_s: Optional[int] = None
    notas_catado: Optional[str] = None
    es_borrador: bool = False
    pasos: Optional[List[str]] = None
    fecha_creacion: datetime



def get_tienda_storage_info(tienda_id: int, limite_mb: Optional[int] = None) -> Dict[str, Any]:
    upload_dir = os.path.join("static", "uploads", "productos")
    total_bytes = 0
    total_archivos = 0
    prefix = f"{tienda_id}_"
    if os.path.isdir(upload_dir):
        for entry in os.scandir(upload_dir):
            if entry.is_file() and entry.name.startswith(prefix):
                try:
                    total_bytes += entry.stat().st_size
                    total_archivos += 1
                except OSError:
                    pass
    
    lim_mb = limite_mb if (limite_mb and limite_mb > 0) else 250
    lim_bytes = lim_mb * 1024 * 1024
    mb_usados = round(total_bytes / (1024 * 1024), 2)
    porcentaje = round((total_bytes / lim_bytes) * 100, 1) if lim_bytes > 0 else 0.0

    return {
        "tienda_id": tienda_id,
        "bytes_usados": total_bytes,
        "mb_usados": mb_usados,
        "limite_mb": lim_mb,
        "porcentaje_usado": min(porcentaje, 100.0),
        "total_archivos": total_archivos,
        "superado": total_bytes >= lim_bytes,
    }


def _sync_product_tasting_notes(db_session: Session, producto_id: int, notas: List[str]) -> None:
    if not notas:
        return
    from core.normalizer import is_valid_tasting_note, SCAFlavorWheelNormalizer, sanitize_text
    
    for nota_raw in notas:
        nom_limpio = (nota_raw or "").strip()
        if not nom_limpio or not is_valid_tasting_note(nom_limpio):
            continue
        clave = sanitize_text(nom_limpio).replace(" ", "-")
        nota = db_session.scalar(select(NotaCata).where(NotaCata.clave_normalizada == clave))
        if not nota:
            nota = NotaCata(clave_normalizada=clave, nombre=nom_limpio.capitalize())
            db_session.add(nota)
            db_session.flush()
        
        sca_match = SCAFlavorWheelNormalizer.normalizar_nota(nom_limpio)
        es_fuera = sca_match is None
        
        rel = db_session.scalar(
            select(ProductoNotaCata).where(
                ProductoNotaCata.producto_id == producto_id,
                ProductoNotaCata.nota_id == nota.id,
            )
        )
        if rel:
            rel.estado = "confirmada"
            rel.confianza = 1.0
        else:
            rel = ProductoNotaCata(
                producto_id=producto_id,
                nota_id=nota.id,
                texto_origen="Registrado en catálogo por tostaduría",
                confianza=1.0,
                version_extractor="manual_store_admin",
                estado="confirmada",
                es_fuera_de_rueda=es_fuera,
            )
            db_session.add(rel)


# --- ENDPOINTS ---

@router.post(
    "/auth/login",
    response_model=StoreAdminLoginResponse,
    summary="Inicio de sesión seguro para administradores de tostadurías con protección anti-fuerza bruta y anti-bot",
)
def store_admin_login(
    payload: StoreAdminLoginRequest,
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> StoreAdminLoginResponse:
    client_ip = get_client_ip(request)
    identifier = payload.email.strip().lower()

    # 1. Verificación de bloqueo temporal anti-fuerza bruta
    is_locked, remaining_secs = anti_brute_force.is_locked_out(client_ip, identifier)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Cuenta bloqueada temporalmente debido a múltiples intentos fallidos. Intenta nuevamente en {remaining_secs} segundos.",
            headers={"Retry-After": str(remaining_secs)},
        )

    # 2. Verificación anti-bot (Turnstile / Captcha)
    if not verify_anti_bot_token(payload.turnstile_token, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fallo en la validación de seguridad anti-bot (Turnstile).",
        )

    # 3. Búsqueda y autenticación del usuario
    # Permitimos ingreso mediante usuario_id explícito o email asociado
    user_id_lookup = payload.usuario_id or identifier

    user_store = db_session.scalars(
        select(UsuarioTienda)
        .where(
            (UsuarioTienda.usuario_id == user_id_lookup)
            | (UsuarioTienda.usuario_id == identifier)
        )
    ).first()

    # Si no se encuentra con lookup directo pero hay contraseña/token, validar
    if not user_store:
        # Registrar intento fallido
        anti_brute_force.record_login_failure(client_ip, identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas o usuario no asignado como administrador de ninguna tostaduría.",
        )

    tienda = db_session.scalars(select(Tienda).where(Tienda.id == user_store.tienda_id)).first()
    if not tienda:
        anti_brute_force.record_login_failure(client_ip, identifier)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tostaduría vinculada a esta cuenta no existe.",
        )

    # Si el usuario tiene contraseña configurada, verificarla
    if getattr(user_store, "password_hash", None):
        if not payload.password or not verify_store_password(payload.password, user_store.password_hash):
            anti_brute_force.record_login_failure(client_ip, identifier)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña incorrecta.",
            )

    # Éxito: restablecer intentos fallidos
    anti_brute_force.record_login_success(client_ip, identifier)

    token = create_store_admin_token(
        usuario_id=user_store.usuario_id,
        tienda_id=tienda.id,
        rol=user_store.rol,
        expires_in_seconds=86400,
    )

    # Auditoría de inicio de sesión exitoso
    log_store_action(
        db_session=db_session,
        tienda_id=tienda.id,
        usuario_id=user_store.usuario_id,
        accion="LOGIN_EXITOSO",
        entidad="usuarios_tienda",
        entidad_id=tienda.id,
        valores_nuevos={"email": identifier, "rol": user_store.rol},
        ip_origen=client_ip,
    )

    return StoreAdminLoginResponse(
        token=token,
        token_type="bearer",
        expires_in=86400,
        usuario_id=user_store.usuario_id,
        tienda_id=tienda.id,
        tienda_nombre=tienda.nombre,
        rol=user_store.rol,
        debe_cambiar_password=bool(getattr(user_store, "debe_cambiar_password", False)),
        scraping_activo=bool(tienda.activo),
    )


@router.post(
    "/auth/cambiar-password",
    summary="Cambiar la clave de acceso del administrador de tienda (1er ingreso o actualización)",
)
def change_store_admin_password(
    payload: StoreChangePasswordRequest,
    request: Request,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    user_store = db_session.scalars(
        select(UsuarioTienda).where(
            UsuarioTienda.usuario_id == ctx.usuario_id,
            UsuarioTienda.tienda_id == ctx.tienda_id,
        )
    ).first()
    if not user_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta de administrador de tienda no encontrada.",
        )

    # Si ya tiene una contraseña previa, verificarla salvo que sea primer ingreso sin password_actual
    if user_store.password_hash and payload.password_actual:
        if not verify_store_password(payload.password_actual, user_store.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual provista es incorrecta.",
            )

    user_store.password_hash = hash_store_password(payload.password_nuevo.strip())
    user_store.debe_cambiar_password = False
    db_session.commit()

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CAMBIO_PASSWORD",
        entidad="usuarios_tienda",
        entidad_id=ctx.tienda_id,
        valores_nuevos={"debe_cambiar_password": False},
        ip_origen=get_client_ip(request),
    )

    return {
        "exito": True,
        "mensaje": "Contraseña actualizada exitosamente. Ya puedes utilizar tu nueva clave de acceso.",
    }



@router.get(
    "/almacenamiento",
    summary="Consultar uso actual y cuota de almacenamiento de imágenes de la tienda",
)
def get_store_storage_quota(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
) -> Dict[str, Any]:
    limite_mb = getattr(ctx.tienda, "limite_almacenamiento_mb", 250) or 250
    return get_tienda_storage_info(ctx.tienda_id, limite_mb)


@router.get(
    "/perfil",
    response_model=StoreAdminProfileResponse,
    summary="Consultar datos de perfil y estado de la tienda asignada",
)
def get_store_profile(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreAdminProfileResponse:
    t = ctx.tienda
    total_prods = db_session.scalar(
        select(func.count(Producto.id)).where(Producto.tienda_id == t.id)
    ) or 0

    last_sync = db_session.scalars(
        select(Sincronizacion)
        .where(Sincronizacion.tienda_id == t.id)
        .order_by(Sincronizacion.id.desc())
    ).first()

    last_sync_time = last_sync.fecha_inicio.isoformat() if (last_sync and last_sync.fecha_inicio) else None
    last_sync_status = last_sync.resultado if last_sync else "nunca"

    _, cooldown_secs = anti_brute_force.check_sync_cooldown(t.id)

    return StoreAdminProfileResponse(
        usuario_id=ctx.usuario_id,
        tienda_id=t.id,
        tienda_nombre=t.nombre,
        tienda_url=t.url_base,
        plataforma=t.plataforma or "desconocida",
        activo=bool(t.activo),
        rol=ctx.rol,
        ultima_sincronizacion=last_sync_time,
        estado_sincronizacion=last_sync_status,
        total_productos=total_prods,
        cooldown_sync_segundos=cooldown_secs,
        logo_url=getattr(t, "logo_url", None),
        telefono_whatsapp=getattr(t, "telefono_whatsapp", None),
        envio_gratis_monto=getattr(t, "envio_gratis_monto", None),
        retiro_en_tienda=bool(getattr(t, "retiro_en_tienda", False)),
        dias_tueste=getattr(t, "dias_tueste", None),
        fecha_ultimo_tueste=getattr(t, "fecha_ultimo_tueste", None).isoformat() if getattr(t, "fecha_ultimo_tueste", None) else None,
        scraping_activo=bool(t.activo),
        limite_almacenamiento_mb=get_tienda_storage_info(t.id, getattr(t, "limite_almacenamiento_mb", 250))["limite_mb"],
        almacenamiento_usado_mb=get_tienda_storage_info(t.id, getattr(t, "limite_almacenamiento_mb", 250))["mb_usados"],
        almacenamiento_porcentaje=get_tienda_storage_info(t.id, getattr(t, "limite_almacenamiento_mb", 250))["porcentaje_usado"],
    )


def _safe_int(val: Any, default: int) -> int:
    if hasattr(val, "default") and isinstance(val.default, int):
        return val.default
    try:
        return int(val)
    except Exception:
        return default


@router.get(
    "/productos",
    response_model=StoreProductsListResponse,
    summary="Listar productos pertenecientes exclusivamente a la tostaduría del administrador",
)
def list_store_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Filtro de búsqueda por nombre o descripción"),
    oculto: Optional[bool] = Query(None, description="Filtrar por productos ocultos del catálogo público"),
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreProductsListResponse:
    page_num = _safe_int(page, 1)
    per_page_num = _safe_int(per_page, 50)
    q_str = q if isinstance(q, str) else (q.default if hasattr(q, "default") and isinstance(q.default, str) else None)
    oculto_bool = oculto if isinstance(oculto, bool) else (oculto.default if hasattr(oculto, "default") and isinstance(oculto.default, bool) else None)

    # Aislamiento multi-inquilino estricto por ctx.tienda_id
    query = (
        select(Producto)
        .options(selectinload(Producto.variantes))
        .where(Producto.tienda_id == ctx.tienda_id)
    )

    if q_str and q_str.strip():
        term = f"%{q_str.strip().lower()}%"
        query = query.where(func.lower(Producto.nombre).like(term))

    if oculto_bool is not None:
        query = query.where(Producto.oculto_catalogo.is_(oculto_bool))

    total = db_session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_paginas = max(1, math.ceil(total / per_page_num))

    offset = (page_num - 1) * per_page_num
    productos = db_session.scalars(
        query.order_by(Producto.nombre.asc()).offset(offset).limit(per_page_num)
    ).all()

    items = []
    for p in productos:
        variantes_dto = [
            StoreProductVariantOutput(
                id=v.id,
                id_variante_externo=v.id_variante_externo,
                opcion=v.opcion,
                formato_gramos=v.formato_gramos,
                precio_clp=v.precio_clp,
                precio_original_clp=v.precio_original_clp,
                en_oferta=bool(v.en_oferta),
                descuento_porcentaje=v.descuento_porcentaje or 0,
                precio_por_kilo=float(v.precio_por_kilo or 0.0),
                disponible=bool(v.disponible),
            )
            for v in (p.variantes or [])
        ]
        c_fuente = p.caracteristicas_fuente or {}
        items.append(
            StoreProductOutput(
                id=p.id,
                tienda_id=p.tienda_id,
                nombre=p.nombre,
                url_detalle=p.url_detalle,
                imagen=p.imagen,
                descripcion=p.descripcion,
                origen=p.pais_origen,
                finca=p.finca,
                variedad=p.variedad,
                proceso=p.proceso,
                tueste=p.tueste,
                sca_score=c_fuente.get('sca_score'),
                notas_cata=c_fuente.get('notas_cata') or [],
                activo=bool(p.activo),
                oculto_catalogo=bool(p.oculto_catalogo),
                es_manual=bool(p.id_externo is None or (c_fuente.get("creacion_manual") is True)),
                variantes=variantes_dto,
            )
        )

    return StoreProductsListResponse(
        total=total,
        page=page_num,
        per_page=per_page_num,
        total_paginas=total_paginas,
        productos=items,
    )


@router.post(
    "/productos",
    response_model=StoreProductOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo producto forzando la vinculación al tienda_id del usuario",
)
def create_store_product(
    payload: StoreProductInput,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreProductOutput:
    # Aislamiento multi-inquilino: el producto se crea forzosamente con ctx.tienda_id
    url_base = ctx.tienda.url_base.rstrip("/")
    slug = payload.nombre.lower().replace(" ", "-").replace("/", "-")
    url_detalle = payload.url_detalle or f"{url_base}/producto/{slug}"

    from domain.search_normalizer import classify_product_category

    caract_init = {}
    if payload.sca_score is not None:
        caract_init['sca_score'] = payload.sca_score
    caract_init['creacion_manual'] = True
    if payload.notas_cata is not None:
        caract_init['notas_cata'] = payload.notas_cata

    prod = Producto(
        tienda_id=ctx.tienda_id,
        nombre=payload.nombre.strip(),
        categoria=classify_product_category(payload.nombre.strip()),
        url_detalle=url_detalle,
        imagen=payload.imagen,
        descripcion=payload.descripcion,
        pais_origen=payload.origen,
        finca=payload.finca,
        variedad=payload.variedad,
        proceso=payload.proceso,
        tueste=payload.tueste,
        caracteristicas_fuente=caract_init,
        activo=payload.activo,
        oculto_catalogo=payload.oculto_catalogo,
    )
    db_session.add(prod)
    db_session.flush()
    if payload.notas_cata:
        _sync_product_tasting_notes(db_session, prod.id, payload.notas_cata)

    variantes_creadas = []
    if payload.variantes:
        for idx, var_in in enumerate(payload.variantes):
            ext_id = var_in.id_variante_externo or f"{prod.id}-v{idx + 1}"
            orig_price = var_in.precio_original_clp or var_in.precio_clp
            gramos = var_in.formato_gramos or 250
            precio_kilo = round((var_in.precio_clp / gramos) * 1000, 2)
            descuento = round(((orig_price - var_in.precio_clp) / orig_price) * 100) if orig_price > var_in.precio_clp else 0

            v = Variante(
                producto_id=prod.id,
                id_variante_externo=ext_id,
                opcion=var_in.opcion,
                formato_gramos=gramos,
                precio_clp=var_in.precio_clp,
                precio_original_clp=orig_price,
                en_oferta=orig_price > var_in.precio_clp,
                descuento_porcentaje=descuento,
                precio_por_kilo=precio_kilo,
                disponible=var_in.disponible,
            )
            db_session.add(v)
            variantes_creadas.append(v)
    else:
        # Variante predeterminada de 250g
        v = Variante(
            producto_id=prod.id,
            id_variante_externo=f"{prod.id}-v1",
            opcion="250g",
            formato_gramos=250,
            precio_clp=9990,
            precio_original_clp=9990,
            en_oferta=False,
            descuento_porcentaje=0,
            precio_por_kilo=39960.0,
            disponible=True,
        )
        db_session.add(v)
        variantes_creadas.append(v)

    db_session.commit()
    db_session.refresh(prod)

    # Auditoría automática de creación
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CREAR_PRODUCTO",
        entidad="productos",
        entidad_id=prod.id,
        valores_nuevos={
            "nombre": prod.nombre,
            "url_detalle": prod.url_detalle,
            "activo": prod.activo,
            "oculto_catalogo": prod.oculto_catalogo,
            "variantes_count": len(variantes_creadas),
        },
        ip_origen=ctx.ip_origen,
    )

    variantes_dto = [
        StoreProductVariantOutput(
            id=v.id,
            id_variante_externo=v.id_variante_externo,
            opcion=v.opcion,
            formato_gramos=v.formato_gramos,
            precio_clp=v.precio_clp,
            precio_original_clp=v.precio_original_clp,
            en_oferta=bool(v.en_oferta),
            descuento_porcentaje=v.descuento_porcentaje or 0,
            precio_por_kilo=float(v.precio_por_kilo or 0.0),
            disponible=bool(v.disponible),
        )
        for v in variantes_creadas
    ]

    c_fuente_creado = prod.caracteristicas_fuente or {}
    return StoreProductOutput(
        id=prod.id,
        tienda_id=prod.tienda_id,
        nombre=prod.nombre,
        url_detalle=prod.url_detalle,
        imagen=prod.imagen,
        descripcion=prod.descripcion,
        origen=prod.pais_origen,
        finca=prod.finca,
        variedad=prod.variedad,
        proceso=prod.proceso,
        tueste=prod.tueste,
        sca_score=c_fuente_creado.get('sca_score'),
        notas_cata=c_fuente_creado.get('notas_cata') or [],
        activo=bool(prod.activo),
        oculto_catalogo=bool(prod.oculto_catalogo),
        es_manual=bool(prod.id_externo is None or (prod.caracteristicas_fuente and prod.caracteristicas_fuente.get("creacion_manual") is True)),
        variantes=variantes_dto,
    )



@router.post(
    "/productos/{producto_id}/imagen",
    response_model=StoreProductImageUploadResponse,
    summary="Subir imagen para un producto creado manualmente",
)
def upload_store_product_image(
    producto_id: int,
    payload: StoreProductImageUploadRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreProductImageUploadResponse:
    prod = db_session.scalars(
        select(Producto).where(Producto.id == producto_id, Producto.tienda_id == ctx.tienda_id)
    ).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado en su catálogo.",
        )
    
    c_fuente = prod.caracteristicas_fuente or {}
    es_manual = prod.id_externo is None or bool(c_fuente.get("creacion_manual"))
    if not es_manual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden subir imágenes locales para productos creados manualmente desde la administración. Los productos de tiendas online sincronizan sus imágenes automáticamente.",
        )
    
    b64_str = payload.imagen_base64.strip()
    if "," in b64_str and b64_str.startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    
    try:
        raw_bytes = base64.b64decode(b64_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cadena Base64 provista es inválida o está corrupta.",
        )
    
    if len(raw_bytes) > 3 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen excede el tamaño máximo permitido de 3 MB.",
        )
    
    ext = ".jpg"
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif raw_bytes.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif raw_bytes.startswith(b"RIFF") and len(raw_bytes) > 12 and raw_bytes[8:12] == b"WEBP":
        ext = ".webp"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagen no soportado. Debe ser WebP, JPEG o PNG.",
        )
    
    limite_mb = getattr(ctx.tienda, "limite_almacenamiento_mb", 250) or 250
    storage = get_tienda_storage_info(ctx.tienda_id, limite_mb)
    if storage["bytes_usados"] + len(raw_bytes) > limite_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Has superado la cuota de almacenamiento de imágenes ({limite_mb} MB). Espacio usado: {storage['mb_usados']} MB. Contacta a soporte para ampliar tu plan.",
        )
    
    target_dir = os.path.join("static", "uploads", "productos")
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{ctx.tienda_id}_{prod.id}_{int(time.time())}{ext}"
    file_path = os.path.join(target_dir, filename)
    
    with open(file_path, "wb") as f_out:
        f_out.write(raw_bytes)
    
    imagen_url = f"/static/uploads/productos/{filename}"
    prod.imagen = imagen_url
    
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="SUBIR_IMAGEN_PRODUCTO",
        entidad="productos",
        entidad_id=prod.id,
        valores_nuevos={"imagen": imagen_url, "bytes": len(raw_bytes)},
        ip_origen=ctx.ip_origen,
    )
    db_session.commit()
    
    updated_storage = get_tienda_storage_info(ctx.tienda_id, limite_mb)
    return StoreProductImageUploadResponse(
        exito=True,
        imagen_url=imagen_url,
        mensaje="Imagen subida y asociada exitosamente al producto.",
        mb_usados=updated_storage["mb_usados"],
        limite_mb=updated_storage["limite_mb"],
        porcentaje_usado=updated_storage["porcentaje_usado"],
    )


@router.put(
    "/productos/{product_id}",
    response_model=StoreProductOutput,
    summary="Modificar un producto de la tienda con verificación estricta de pertenencia (RBAC/Tenancy)",
)
def update_store_product(
    product_id: int,
    payload: StoreProductInput,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreProductOutput:
    prod = db_session.scalars(
        select(Producto)
        .options(selectinload(Producto.variantes))
        .where(Producto.id == product_id)
    ).first()

    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    # Verificación de seguridad multi-inquilino (RBAC / Tenancy)
    if prod.tienda_id != ctx.tienda_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: este producto pertenece a otra tostaduría y no tienes autorización para modificarlo.",
        )

    valores_previos = {
        "nombre": prod.nombre,
        "descripcion": prod.descripcion,
        "imagen": prod.imagen,
        "origen": prod.pais_origen,
        "finca": prod.finca,
        "variedad": prod.variedad,
        "proceso": prod.proceso,
        "tueste": prod.tueste,
        "activo": prod.activo,
        "oculto_catalogo": prod.oculto_catalogo,
    }

    from domain.search_normalizer import classify_product_category

    prod.nombre = payload.nombre.strip()
    prod.categoria = classify_product_category(prod.nombre)
    if payload.url_detalle:
        prod.url_detalle = payload.url_detalle
    if payload.imagen is not None:
        if payload.imagen.strip():
            prod.imagen = payload.imagen.strip()
        else:
            prod.imagen = None
    prod.descripcion = payload.descripcion
    prod.pais_origen = payload.origen
    prod.finca = payload.finca
    prod.variedad = payload.variedad
    prod.proceso = payload.proceso
    prod.tueste = payload.tueste
    prod.activo = payload.activo
    prod.oculto_catalogo = payload.oculto_catalogo

    caract = dict(prod.caracteristicas_fuente or {})
    if payload.sca_score is not None:
        caract["sca_score"] = payload.sca_score
    if payload.notas_cata is not None:
        caract["notas_cata"] = payload.notas_cata
        _sync_product_tasting_notes(db_session, prod.id, payload.notas_cata)
    prod.caracteristicas_fuente = caract

    # Actualizar o insertar variantes si se especifican
    if payload.variantes:
        existing_vars = {v.id_variante_externo: v for v in prod.variantes}
        for idx, var_in in enumerate(payload.variantes):
            ext_id = var_in.id_variante_externo or f"{prod.id}-v{idx + 1}"
            orig_price = var_in.precio_original_clp or var_in.precio_clp
            gramos = var_in.formato_gramos or 250
            precio_kilo = round((var_in.precio_clp / gramos) * 1000, 2)
            descuento = round(((orig_price - var_in.precio_clp) / orig_price) * 100) if orig_price > var_in.precio_clp else 0

            if ext_id in existing_vars:
                ev = existing_vars[ext_id]
                ev.opcion = var_in.opcion
                ev.formato_gramos = gramos
                ev.precio_clp = var_in.precio_clp
                ev.precio_original_clp = orig_price
                ev.en_oferta = orig_price > var_in.precio_clp
                ev.descuento_porcentaje = descuento
                ev.precio_por_kilo = precio_kilo
                ev.disponible = var_in.disponible
            else:
                nv = Variante(
                    producto_id=prod.id,
                    id_variante_externo=ext_id,
                    opcion=var_in.opcion,
                    formato_gramos=gramos,
                    precio_clp=var_in.precio_clp,
                    precio_original_clp=orig_price,
                    en_oferta=orig_price > var_in.precio_clp,
                    descuento_porcentaje=descuento,
                    precio_por_kilo=precio_kilo,
                    disponible=var_in.disponible,
                )
                db_session.add(nv)

    db_session.commit()
    db_session.refresh(prod)

    valores_nuevos = {
        "nombre": prod.nombre,
        "descripcion": prod.descripcion,
        "imagen": prod.imagen,
        "origen": prod.pais_origen,
        "finca": prod.finca,
        "variedad": prod.variedad,
        "proceso": prod.proceso,
        "tueste": prod.tueste,
        "activo": prod.activo,
        "oculto_catalogo": prod.oculto_catalogo,
    }

    # Auditoría automática de edición
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="EDITAR_PRODUCTO",
        entidad="productos",
        entidad_id=prod.id,
        valores_previos=valores_previos,
        valores_nuevos=valores_nuevos,
        ip_origen=ctx.ip_origen,
    )

    variantes_dto = [
        StoreProductVariantOutput(
            id=v.id,
            id_variante_externo=v.id_variante_externo,
            opcion=v.opcion,
            formato_gramos=v.formato_gramos,
            precio_clp=v.precio_clp,
            precio_original_clp=v.precio_original_clp,
            en_oferta=bool(v.en_oferta),
            descuento_porcentaje=v.descuento_porcentaje or 0,
            precio_por_kilo=float(v.precio_por_kilo or 0.0),
            disponible=bool(v.disponible),
        )
        for v in (prod.variantes or [])
    ]

    c_fuente_upd = prod.caracteristicas_fuente or {}
    return StoreProductOutput(
        id=prod.id,
        tienda_id=prod.tienda_id,
        nombre=prod.nombre,
        url_detalle=prod.url_detalle,
        imagen=prod.imagen,
        descripcion=prod.descripcion,
        origen=prod.pais_origen,
        finca=prod.finca,
        variedad=prod.variedad,
        proceso=prod.proceso,
        tueste=prod.tueste,
        sca_score=c_fuente_upd.get('sca_score'),
        notas_cata=c_fuente_upd.get('notas_cata') or [],
        activo=bool(prod.activo),
        oculto_catalogo=bool(prod.oculto_catalogo),
        es_manual=bool(prod.id_externo is None or (prod.caracteristicas_fuente and prod.caracteristicas_fuente.get("creacion_manual") is True)),
        variantes=variantes_dto,
    )


@router.post(
    "/sincronizar",
    response_model=StoreSyncActionResponse,
    summary="Disparar sincronización manual voluntaria para la tienda activa con cooldown de 30 minutos",
)
def sync_own_store(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreSyncActionResponse:
    # 1. Verificación de cooldown (30 min)
    in_cooldown, remaining_secs = anti_brute_force.check_sync_cooldown(ctx.tienda_id, cooldown_seconds=1800)
    if in_cooldown:
        mins = remaining_secs // 60
        secs = remaining_secs % 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Sincronización en período de enfriamiento (cooldown). Podrás iniciar otra sincronización en {mins}m {secs}s.",
            headers={"Retry-After": str(remaining_secs)},
        )

    # 2. Registrar ejecución y disparar scraper
    anti_brute_force.record_sync_execution(ctx.tienda_id)

    tienda_dict = {
        "id": ctx.tienda.id,
        "nombre": ctx.tienda.nombre,
        "url_base": ctx.tienda.url_base,
        "plataforma": ctx.tienda.plataforma or "desconocida",
    }

    db_manager = DatabaseManager()
    res = sincronizar_tienda(tienda_dict, db=db_manager)

    # 3. Registrar en sincronizaciones_log
    sync_log = SincronizacionLog(
        estado="OK" if res["exito"] else "ERROR",
        productos_nuevos=res.get("productos_nuevos", 0),
        productos_actualizados=res.get("productos_actualizados", 0),
        duracion_segundos=res.get("duracion_segundos", 0.0),
        mensaje_error=res.get("error"),
    )
    db_session.add(sync_log)
    db_session.commit()

    # 4. Auditoría de la acción
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="INICIAR_SYNC",
        entidad="tiendas",
        entidad_id=ctx.tienda_id,
        valores_nuevos={
            "exito": res["exito"],
            "total_productos": res["total_productos"],
            "productos_nuevos": res["productos_nuevos"],
            "productos_actualizados": res["productos_actualizados"],
            "duracion_segundos": res["duracion_segundos"],
        },
        ip_origen=ctx.ip_origen,
    )

    mensaje = (
        f"Catálogo de {ctx.tienda.nombre} sincronizado exitosamente: {res['total_productos']} productos revisados "
        f"({res['productos_nuevos']} nuevos, {res['productos_actualizados']} actualizados) en {res['duracion_segundos']}s."
        if res["exito"]
        else f"Error durante la sincronización: {res['error']}"
    )

    return StoreSyncActionResponse(
        exito=res["exito"],
        tienda_id=ctx.tienda_id,
        tienda_nombre=ctx.tienda.nombre,
        total_productos=res["total_productos"],
        productos_nuevos=res["productos_nuevos"],
        productos_actualizados=res["productos_actualizados"],
        duracion_segundos=res["duracion_segundos"],
        error=res["error"],
        mensaje=mensaje,
        cooldown_activo_segundos=1800,
    )


@router.get(
    "/auditoria",
    response_model=AuditLogsListResponse,
    summary="Consultar historial de auditoría de acciones realizadas por los administradores de la tienda",
)
def list_store_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> AuditLogsListResponse:
    query = (
        select(AuditoriaAccionesTienda)
        .where(AuditoriaAccionesTienda.tienda_id == ctx.tienda_id)
        .order_by(AuditoriaAccionesTienda.fecha_registro.desc())
    )

    page_num = _safe_int(page, 1)
    per_page_num = _safe_int(per_page, 30)

    total = db_session.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page_num - 1) * per_page_num
    logs = db_session.scalars(query.offset(offset).limit(per_page_num)).all()

    items = [
        AuditLogItem(
            id=l.id,
            tienda_id=l.tienda_id,
            usuario_id=l.usuario_id,
            accion=l.accion,
            entidad=l.entidad,
            entidad_id=l.entidad_id,
            valores_previos=l.valores_previos,
            valores_nuevos=l.valores_nuevos,
            ip_origen=l.ip_origen,
            fecha_registro=l.fecha_registro,
        )
        for l in logs
    ]

    return AuditLogsListResponse(
        total=total,
        page=page_num,
        per_page=per_page_num,
        registros=items,
    )


# --- RECETAS OFICIALES DE LA TOSTADURÍA ---

@router.get(
    "/recetas",
    response_model=List[StoreRecipeOutput],
    summary="Listar recetas oficiales de la tostaduría para sus cafés",
)
def list_store_recipes(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> List[StoreRecipeOutput]:
    stmt = (
        select(Receta, Producto.nombre.label("producto_nombre"))
        .outerjoin(Producto, Receta.producto_id == Producto.id)
        .where(Receta.tienda_id == ctx.tienda_id)
        .order_by(Receta.fecha_creacion.desc())
    )
    results = db_session.execute(stmt).all()
    output = []
    for r, prod_nombre in results:
        output.append(
            StoreRecipeOutput(
                id=r.id,
                producto_id=r.producto_id,
                producto_nombre=prod_nombre,
                tienda_id=r.tienda_id,
                nombre_receta=r.nombre_receta,
                metodo=r.metodo,
                dosis_cafe_g=float(r.dosis_cafe_g),
                agua_ml=float(r.agua_ml),
                ratio=r.ratio,
                molino_usado=r.molino_usado,
                grosor_molienda=r.grosor_molienda,
                temperatura_c=r.temperatura_c,
                tiempo_total_s=r.tiempo_total_s,
                notas_catado=r.notas_catado,
                es_borrador=bool(getattr(r, 'es_borrador', False)),
                pasos=r.pasos if isinstance(r.pasos, list) else None,
                fecha_creacion=r.fecha_creacion,
            )
        )
    return output


@router.post(
    "/recetas",
    response_model=StoreRecipeOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Crear receta oficial para un café de la tostaduría",
)
def create_store_recipe(
    payload: StoreRecipeInput,
    request: Request,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreRecipeOutput:
    # Aislamiento multi-tenant estricto: el producto debe pertenecer a ctx.tienda_id
    product = db_session.scalars(
        select(Producto).where(Producto.id == payload.producto_id, Producto.tienda_id == ctx.tienda_id)
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar un café existente en tu catálogo. Si no tienes productos aún, crea uno primero.",
        )

    ratio_calculado = payload.ratio
    if not ratio_calculado and payload.dosis_cafe_g > 0:
        ratio_val = round(payload.agua_ml / payload.dosis_cafe_g, 1)
        ratio_calculado = f"1:{ratio_val}"

    # Limpiar lista de pasos eliminando vacíos
    pasos_limpios = (
        [p.strip() for p in payload.pasos if p and p.strip()]
        if payload.pasos else None
    )

    nueva_receta = Receta(
        dispositivo_uuid=f"store-{ctx.tienda_id}",
        producto_id=product.id,
        tienda_id=ctx.tienda_id,
        autor_tipo="tostaduria",
        es_publica=not payload.es_borrador,
        es_borrador=payload.es_borrador,
        nombre_receta=payload.nombre_receta.strip(),
        metodo=payload.metodo.strip(),
        dosis_cafe_g=payload.dosis_cafe_g,
        agua_ml=payload.agua_ml,
        ratio=ratio_calculado,
        molino_usado=payload.molino_usado.strip() if payload.molino_usado else None,
        grosor_molienda=payload.grosor_molienda.strip() if payload.grosor_molienda else None,
        temperatura_c=payload.temperatura_c,
        tiempo_total_s=payload.tiempo_total_s,
        notas_catado=payload.notas_catado.strip() if payload.notas_catado else None,
        pasos=pasos_limpios,
        reintentar=True,
    )
    db_session.add(nueva_receta)
    db_session.flush()

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CREAR_RECETA_PRODUCTO",
        entidad="recetas",
        entidad_id=nueva_receta.id,
        valores_nuevos={
            "nombre": nueva_receta.nombre_receta,
            "producto_id": product.id,
            "metodo": nueva_receta.metodo,
            "es_borrador": nueva_receta.es_borrador,
        },
        ip_origen=get_client_ip(request),
    )
    db_session.commit()
    db_session.refresh(nueva_receta)

    return StoreRecipeOutput(
        id=nueva_receta.id,
        producto_id=nueva_receta.producto_id,
        producto_nombre=product.nombre,
        tienda_id=nueva_receta.tienda_id,
        nombre_receta=nueva_receta.nombre_receta,
        metodo=nueva_receta.metodo,
        dosis_cafe_g=float(nueva_receta.dosis_cafe_g),
        agua_ml=float(nueva_receta.agua_ml),
        ratio=nueva_receta.ratio,
        molino_usado=nueva_receta.molino_usado,
        grosor_molienda=nueva_receta.grosor_molienda,
        temperatura_c=nueva_receta.temperatura_c,
        tiempo_total_s=nueva_receta.tiempo_total_s,
        notas_catado=nueva_receta.notas_catado,
        es_borrador=nueva_receta.es_borrador,
        pasos=nueva_receta.pasos,
        fecha_creacion=nueva_receta.fecha_creacion,
    )



@router.put(
    "/recetas/{receta_id}",
    response_model=StoreRecipeOutput,
    status_code=status.HTTP_200_OK,
    summary="Modificar una receta oficial existente de la tostaduría",
)
def update_store_recipe(
    receta_id: int,
    payload: StoreRecipeInput,
    request: Request,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreRecipeOutput:
    receta = db_session.scalars(
        select(Receta).where(Receta.id == receta_id, Receta.tienda_id == ctx.tienda_id)
    ).first()
    if not receta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receta no encontrada o no pertenece a tu tostaduría.",
        )

    product = db_session.scalars(
        select(Producto).where(Producto.id == payload.producto_id, Producto.tienda_id == ctx.tienda_id)
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El café seleccionado no existe en tu catálogo o no pertenece a tu tostaduría.",
        )

    ratio_calculado = payload.ratio
    if not ratio_calculado and payload.dosis_cafe_g > 0:
        ratio_val = round(payload.agua_ml / payload.dosis_cafe_g, 1)
        ratio_calculado = f"1:{ratio_val}"

    pasos_limpios = (
        [p.strip() for p in payload.pasos if p and p.strip()]
        if payload.pasos else None
    )

    valores_previos = {
        "nombre": receta.nombre_receta,
        "producto_id": receta.producto_id,
        "metodo": receta.metodo,
        "es_borrador": receta.es_borrador,
    }

    receta.producto_id = product.id
    receta.nombre_receta = payload.nombre_receta.strip()
    receta.metodo = payload.metodo.strip()
    receta.dosis_cafe_g = payload.dosis_cafe_g
    receta.agua_ml = payload.agua_ml
    receta.ratio = ratio_calculado
    receta.molino_usado = payload.molino_usado.strip() if payload.molino_usado else None
    receta.grosor_molienda = payload.grosor_molienda.strip() if payload.grosor_molienda else None
    receta.temperatura_c = payload.temperatura_c
    receta.tiempo_total_s = payload.tiempo_total_s
    receta.notas_catado = payload.notas_catado.strip() if payload.notas_catado else None
    receta.es_borrador = payload.es_borrador
    receta.es_publica = not payload.es_borrador
    receta.pasos = pasos_limpios

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="MODIFICAR_RECETA_PRODUCTO",
        entidad="recetas",
        entidad_id=receta.id,
        valores_previos=valores_previos,
        valores_nuevos={
            "nombre": receta.nombre_receta,
            "producto_id": product.id,
            "metodo": receta.metodo,
            "es_borrador": receta.es_borrador,
        },
        ip_origen=get_client_ip(request),
    )
    db_session.commit()
    db_session.refresh(receta)

    return StoreRecipeOutput(
        id=receta.id,
        producto_id=receta.producto_id,
        producto_nombre=product.nombre,
        tienda_id=receta.tienda_id,
        nombre_receta=receta.nombre_receta,
        metodo=receta.metodo,
        dosis_cafe_g=float(receta.dosis_cafe_g),
        agua_ml=float(receta.agua_ml),
        ratio=receta.ratio,
        molino_usado=receta.molino_usado,
        grosor_molienda=receta.grosor_molienda,
        temperatura_c=receta.temperatura_c,
        tiempo_total_s=receta.tiempo_total_s,
        notas_catado=receta.notas_catado,
        es_borrador=receta.es_borrador,
        pasos=receta.pasos,
        fecha_creacion=receta.fecha_creacion,
    )


@router.delete(
    "/recetas/{receta_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar una receta oficial de la tostaduría",
)
def delete_store_recipe(
    receta_id: int,
    request: Request,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    receta = db_session.scalars(
        select(Receta).where(Receta.id == receta_id, Receta.tienda_id == ctx.tienda_id)
    ).first()
    if not receta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receta no encontrada o no pertenece a tu tostaduría.",
        )

    db_session.delete(receta)
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="ELIMINAR_RECETA_PRODUCTO",
        entidad="recetas",
        entidad_id=receta_id,
        valores_previos={"nombre": receta.nombre_receta, "producto_id": receta.producto_id},
        ip_origen=get_client_ip(request),
    )
    db_session.commit()
    return {"status": "success", "message": "Receta eliminada correctamente."}


# --- GESTIÓN DE PEDIDOS Y VENTAS POR WHATSAPP (MERCHANT) ---

@router.put(
    "/whatsapp/config",
    summary="Actualizar número de WhatsApp comercial de la tostaduría",
)
def update_store_whatsapp_config(
    payload: StoreWhatsAppConfigRequest,
    request: Request,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    tienda = db_session.get(Tienda, ctx.tienda_id)
    if not tienda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tienda no encontrada.")

    val = payload.telefono_whatsapp
    if val:
        val = val.strip()
        cleaned = ("+" if val.startswith("+") else "") + "".join(c for c in val if c.isdigit())
        tienda.telefono_whatsapp = cleaned or None
    else:
        tienda.telefono_whatsapp = None

    db_session.commit()
    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="ACTUALIZAR_WHATSAPP_CONFIG",
        entidad="tiendas",
        entidad_id=ctx.tienda_id,
        valores_nuevos={"telefono_whatsapp": tienda.telefono_whatsapp},
        ip_origen=get_client_ip(request),
    )
    return {
        "status": "success",
        "telefono_whatsapp": tienda.telefono_whatsapp,
        "mensaje": "Número de WhatsApp comercial actualizado correctamente.",
    }


@router.get(
    "/whatsapp/pedidos",
    response_model=List[StoreWhatsAppOrderOutput],
    summary="Listado de pedidos enviados vía WhatsApp por usuarios a esta tostaduría",
)
def list_store_whatsapp_orders(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> List[StoreWhatsAppOrderOutput]:
    pedidos = db_session.scalars(
        select(PedidoWhatsApp)
        .where(PedidoWhatsApp.tienda_id == ctx.tienda_id)
        .order_by(PedidoWhatsApp.fecha_creacion.desc())
    ).all()
    return pedidos


@router.get(
    "/whatsapp/metricas",
    response_model=StoreWhatsAppMetricsOutput,
    summary="Métricas de ventas solicitadas por WhatsApp y proyección financiera",
)
def get_store_whatsapp_metrics(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreWhatsAppMetricsOutput:
    since_30d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

    stmt = (
        select(
            func.coalesce(func.sum(PedidoWhatsApp.monto_total_clp), 0).label("total_monto"),
            func.count(PedidoWhatsApp.id).label("total_pedidos"),
        )
        .where(
            PedidoWhatsApp.tienda_id == ctx.tienda_id,
            PedidoWhatsApp.fecha_creacion >= since_30d,
        )
    )
    row = db_session.execute(stmt).one()
    total_monto_int = int(row[0] or 0)
    total_pedidos_int = int(row[1] or 0)
    incremento_estimado = round(total_monto_int * 0.18)

    monto_fmt = f"{total_monto_int:,.0f}".replace(",", ".")
    texto = (
        f"Tus clientes han solicitado ${monto_fmt} CLP en pedidos por WhatsApp este mes. "
        "Si gestionaras los pagos directamente en la plataforma con la futura pasarela Cafesitios, "
        "podrías aumentar tu tasa de conversión en un 18% estimado y automatizar la confirmación de inventario."
    )

    return StoreWhatsAppMetricsOutput(
        ventas_whatsapp_30d=total_monto_int,
        total_pedidos_30d=total_pedidos_int,
        incremento_estimado_clp=incremento_estimado,
        texto_proyeccion=texto,
    )


# --- FASE 2: GESTIÓN DE CATÁLOGOS, PROBADOR Y SUCURSALES ---

@router.put(
    "/perfil",
    response_model=StoreAdminProfileResponse,
    summary="Actualizar información de marca, ubicación y contacto de la tostaduría",
)
def update_store_profile(
    payload: StoreProfileUpdateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreAdminProfileResponse:
    t = ctx.tienda
    previos = {
        "direccion": t.direccion,
        "comuna": t.comuna,
        "latitud": float(t.latitud) if t.latitud else None,
        "longitud": float(t.longitud) if t.longitud else None,
        "logo_url": t.logo_url,
        "telefono_whatsapp": t.telefono_whatsapp,
    }

    if payload.direccion is not None:
        t.direccion = payload.direccion.strip() or None
    if payload.comuna is not None:
        t.comuna = payload.comuna.strip() or None
    if payload.latitud is not None:
        t.latitud = payload.latitud
    if payload.longitud is not None:
        t.longitud = payload.longitud
    if payload.logo_url is not None:
        t.logo_url = payload.logo_url.strip() or None
    if payload.telefono_whatsapp is not None:
        t.telefono_whatsapp = payload.telefono_whatsapp.strip() or None
    if payload.envio_gratis_monto is not None:
        t.envio_gratis_monto = payload.envio_gratis_monto if payload.envio_gratis_monto > 0 else None
    if payload.retiro_en_tienda is not None:
        t.retiro_en_tienda = bool(payload.retiro_en_tienda)
    if payload.dias_tueste is not None:
        t.dias_tueste = payload.dias_tueste.strip() or None
    if payload.fecha_ultimo_tueste is not None:
        if payload.fecha_ultimo_tueste.strip():
            from datetime import date
            t.fecha_ultimo_tueste = date.fromisoformat(payload.fecha_ultimo_tueste.strip())
        else:
            t.fecha_ultimo_tueste = None

    t.fecha_actualizacion = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.commit()
    db_session.refresh(t)

    nuevos = {
        "direccion": t.direccion,
        "comuna": t.comuna,
        "latitud": float(t.latitud) if t.latitud else None,
        "longitud": float(t.longitud) if t.longitud else None,
        "logo_url": t.logo_url,
        "telefono_whatsapp": t.telefono_whatsapp,
    }

    log_store_action(
        db_session=db_session,
        tienda_id=t.id,
        usuario_id=ctx.usuario_id,
        accion="UPDATE_PERFIL",
        entidad="tiendas",
        entidad_id=t.id,
        valores_previos=previos,
        valores_nuevos=nuevos,
        ip_origen=ctx.ip_origen,
    )

    return get_store_profile(ctx=ctx, db_session=db_session)


@router.get(
    "/catalogos",
    response_model=List[StoreCatalogItem],
    summary="Listar URLs de catálogo y colecciones configuradas para la tostaduría",
)
def list_store_catalogs(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> List[StoreCatalogItem]:
    cats = db_session.scalars(
        select(TiendaCatalogo)
        .where(TiendaCatalogo.tienda_id == ctx.tienda_id)
        .order_by(TiendaCatalogo.id.asc())
    ).all()
    return [StoreCatalogItem.model_validate(c) for c in cats]


@router.post(
    "/catalogos",
    response_model=StoreCatalogItem,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva URL de colección para scraping de la tostaduría",
)
def create_store_catalog(
    payload: StoreCatalogCreateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreCatalogItem:
    url_limpia = payload.url_catalogo.strip()
    nuevo = TiendaCatalogo(
        tienda_id=ctx.tienda_id,
        url_catalogo=url_limpia,
        etiqueta=payload.etiqueta.strip() if payload.etiqueta else None,
        activa=True,
    )
    db_session.add(nuevo)
    db_session.commit()
    db_session.refresh(nuevo)

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CREATE_CATALOGO",
        entidad="tienda_catalogos",
        entidad_id=nuevo.id,
        valores_previos=None,
        valores_nuevos={"url_catalogo": nuevo.url_catalogo, "etiqueta": nuevo.etiqueta},
        ip_origen=ctx.ip_origen,
    )
    return StoreCatalogItem.model_validate(nuevo)


@router.delete(
    "/catalogos/{catalogo_id}",
    summary="Eliminar una URL de colección de la tostaduría",
)
def delete_store_catalog(
    catalogo_id: int,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    cat = db_session.scalars(
        select(TiendaCatalogo).where(
            TiendaCatalogo.id == catalogo_id,
            TiendaCatalogo.tienda_id == ctx.tienda_id,
        )
    ).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catálogo con ID {catalogo_id} no encontrado en tu tostaduría.",
        )

    prev = {"url_catalogo": cat.url_catalogo, "etiqueta": cat.etiqueta}
    db_session.delete(cat)
    db_session.commit()

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="DELETE_CATALOGO",
        entidad="tienda_catalogos",
        entidad_id=catalogo_id,
        valores_previos=prev,
        valores_nuevos=None,
        ip_origen=ctx.ip_origen,
    )
    return {"exito": True, "eliminado_id": catalogo_id}


@router.post(
    "/catalogos/probar",
    response_model=CatalogTestResponse,
    summary="Probar en seco (dry-run) si una nueva URL de colección es legible con los drivers",
)
def test_new_catalog_url(
    payload: StoreCatalogCreateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
) -> CatalogTestResponse:
    test_req = CatalogTestRequest(
        nombre=ctx.tienda.nombre,
        url_catalogo=payload.url_catalogo.strip(),
        plataforma=ctx.tienda.plataforma or "auto",
    )
    return test_store_catalog(test_req)


# --- CRUD DE SUCURSALES FÍSICAS DE LA TOSTADURÍA ---

@router.get(
    "/sucursales",
    response_model=List[StoreBranchItem],
    summary="Listar sucursales y cafeterías físicas pertenecientes a la tostaduría",
)
def list_store_branches(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> List[StoreBranchItem]:
    branches = db_session.scalars(
        select(SucursalTienda)
        .where(SucursalTienda.tienda_id == ctx.tienda_id)
        .order_by(SucursalTienda.id.asc())
    ).all()
    return [StoreBranchItem.model_validate(b) for b in branches]


@router.post(
    "/sucursales",
    response_model=StoreBranchItem,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva sucursal o cafetería física para la tostaduría",
)
def create_store_branch(
    payload: StoreBranchCreateUpdateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreBranchItem:
    nueva = SucursalTienda(
        tienda_id=ctx.tienda_id,
        nombre=payload.nombre.strip(),
        direccion=payload.direccion.strip() if payload.direccion else None,
        comuna=payload.comuna.strip() if payload.comuna else None,
        region=payload.region.strip() if payload.region else None,
        latitud=payload.latitud,
        longitud=payload.longitud,
        activo=payload.activo,
    )
    db_session.add(nueva)
    db_session.commit()
    db_session.refresh(nueva)

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CREATE_SUCURSAL",
        entidad="sucursales_tienda",
        entidad_id=nueva.id,
        valores_previos=None,
        valores_nuevos={"nombre": nueva.nombre, "comuna": nueva.comuna},
        ip_origen=ctx.ip_origen,
    )
    return StoreBranchItem.model_validate(nueva)


@router.put(
    "/sucursales/{sucursal_id}",
    response_model=StoreBranchItem,
    summary="Actualizar los datos de una sucursal física de la tostaduría",
)
def update_store_branch(
    sucursal_id: int,
    payload: StoreBranchCreateUpdateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreBranchItem:
    suc = db_session.scalars(
        select(SucursalTienda).where(
            SucursalTienda.id == sucursal_id,
            SucursalTienda.tienda_id == ctx.tienda_id,
        )
    ).first()
    if not suc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sucursal con ID {sucursal_id} no encontrada en tu tostaduría.",
        )

    prev = {"nombre": suc.nombre, "direccion": suc.direccion, "comuna": suc.comuna}
    suc.nombre = payload.nombre.strip()
    suc.direccion = payload.direccion.strip() if payload.direccion else None
    suc.comuna = payload.comuna.strip() if payload.comuna else None
    suc.region = payload.region.strip() if payload.region else None
    suc.latitud = payload.latitud
    suc.longitud = payload.longitud
    suc.activo = payload.activo
    suc.fecha_actualizacion = datetime.now(timezone.utc).replace(tzinfo=None)

    db_session.commit()
    db_session.refresh(suc)

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="UPDATE_SUCURSAL",
        entidad="sucursales_tienda",
        entidad_id=suc.id,
        valores_previos=prev,
        valores_nuevos={"nombre": suc.nombre, "direccion": suc.direccion, "comuna": suc.comuna},
        ip_origen=ctx.ip_origen,
    )
    return StoreBranchItem.model_validate(suc)


@router.delete(
    "/sucursales/{sucursal_id}",
    summary="Eliminar una sucursal física de la tostaduría",
)
def delete_store_branch(
    sucursal_id: int,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    suc = db_session.scalars(
        select(SucursalTienda).where(
            SucursalTienda.id == sucursal_id,
            SucursalTienda.tienda_id == ctx.tienda_id,
        )
    ).first()
    if not suc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sucursal con ID {sucursal_id} no encontrada en tu tostaduría.",
        )

    prev = {"nombre": suc.nombre, "comuna": suc.comuna}
    db_session.delete(suc)
    db_session.commit()

    log_store_action(
        db_session=db_session,
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="DELETE_SUCURSAL",
        entidad="sucursales_tienda",
        entidad_id=sucursal_id,
        valores_previos=prev,
        valores_nuevos=None,
        ip_origen=ctx.ip_origen,
    )
    return {"exito": True, "eliminado_id": sucursal_id}


@router.get(
    "/telemetria/resumen",
    response_model=StoreTelemetrySummaryResponse,
    summary="Resumen de telemetría comercial: clics salientes, favoritos y top cafés con mayor demanda",
)
def get_store_telemetry_summary(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreTelemetrySummaryResponse:
    clics_outbound = db_session.scalar(
        select(func.count(InteraccionClic.id))
        .join(Producto, InteraccionClic.producto_id == Producto.id)
        .where(
            Producto.tienda_id == ctx.tienda_id,
            InteraccionClic.tipo_evento.ilike("%outbound%"),
        )
    ) or 0

    favoritos = db_session.scalar(
        select(func.count(InteraccionClic.id))
        .join(Producto, InteraccionClic.producto_id == Producto.id)
        .where(
            Producto.tienda_id == ctx.tienda_id,
            InteraccionClic.tipo_evento.ilike("%favorite%"),
        )
    ) or 0

    comparador = db_session.scalar(
        select(func.count(InteraccionClic.id))
        .join(Producto, InteraccionClic.producto_id == Producto.id)
        .where(
            Producto.tienda_id == ctx.tienda_id,
            InteraccionClic.tipo_evento.ilike("%compare%"),
        )
    ) or 0

    top_rows = db_session.execute(
        select(
            Producto.id,
            Producto.nombre,
            func.count(InteraccionClic.id).label("total_clics")
        )
        .join(InteraccionClic, Producto.id == InteraccionClic.producto_id)
        .where(Producto.tienda_id == ctx.tienda_id)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.count(InteraccionClic.id).desc())
        .limit(3)
    ).all()

    top_cafes = [
        TopCoffeeInterestItem(producto_id=r[0], nombre=r[1], total_clics=r[2])
        for r in top_rows
    ]

    return StoreTelemetrySummaryResponse(
        tienda_id=ctx.tienda_id,
        clics_salientes_totales=int(clics_outbound),
        total_favoritos_guardados=int(favoritos),
        apariciones_comparador=int(comparador),
        top_cafes=top_cafes,
    )


@router.get(
    "/productos/inconsistencias",
    response_model=StoreInconsistenciesResponse,
    summary="Bandeja de inconsistencias de scraping para la tienda (precios $0, gramajes dudosos, no café)",
)
def get_store_product_inconsistencies(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreInconsistenciesResponse:
    prods = db_session.scalars(
        select(Producto)
        .options(selectinload(Producto.variantes))
        .where(Producto.tienda_id == ctx.tienda_id)
    ).all()

    inconsistencias: List[StoreInconsistencyItem] = []
    for p in prods:
        if p.categoria and p.categoria != "cafe":
            inconsistencias.append(
                StoreInconsistencyItem(
                    producto_id=p.id,
                    nombre=p.nombre,
                    tipo_inconsistencia="CATEGORIA_NO_CAFE",
                    detalle=f"Categorizado como '{p.categoria}' en lugar de café de especialidad.",
                    url_detalle=p.url_detalle,
                )
            )
        if not p.imagen:
            inconsistencias.append(
                StoreInconsistencyItem(
                    producto_id=p.id,
                    nombre=p.nombre,
                    tipo_inconsistencia="SIN_IMAGEN",
                    detalle="El producto no posee imagen de empaque o portada.",
                    url_detalle=p.url_detalle,
                )
            )
        if not p.variantes:
            inconsistencias.append(
                StoreInconsistencyItem(
                    producto_id=p.id,
                    nombre=p.nombre,
                    tipo_inconsistencia="SIN_VARIANTES",
                    detalle="El producto no tiene ningún formato o precio registrado.",
                    url_detalle=p.url_detalle,
                )
            )
        else:
            for v in p.variantes:
                if (v.precio_clp or 0) <= 0:
                    inconsistencias.append(
                        StoreInconsistencyItem(
                            producto_id=p.id,
                            nombre=p.nombre,
                            tipo_inconsistencia="PRECIO_INVALIDO",
                            detalle=f"Variante '{v.opcion}' tiene precio $0 CLP.",
                            url_detalle=p.url_detalle,
                        )
                    )
                if (v.formato_gramos or 0) <= 0 or (v.formato_gramos or 0) > 10000:
                    inconsistencias.append(
                        StoreInconsistencyItem(
                            producto_id=p.id,
                            nombre=p.nombre,
                            tipo_inconsistencia="GRAMAJE_DUDOSO",
                            detalle=f"Variante '{v.opcion}' registra {v.formato_gramos}g fuera del rango típico.",
                            url_detalle=p.url_detalle,
                        )
                    )

    return StoreInconsistenciesResponse(
        total_inconsistencias=len(inconsistencias),
        inconsistencias=inconsistencias,
    )


@router.get(
    "/analitica/benchmark",
    response_model=StoreBenchmarkResponse,
    summary="Benchmark privado de precios frente a la mediana y promedio del mercado nacional",
)
def get_store_price_benchmark(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreBenchmarkResponse:
    tienda_avg_kilo = db_session.scalar(
        select(func.avg(Variante.precio_por_kilo))
        .join(Producto, Variante.producto_id == Producto.id)
        .where(
            Producto.tienda_id == ctx.tienda_id,
            Producto.activo.is_(True),
            Producto.categoria == "cafe",
            Variante.disponible.is_(True),
            Variante.precio_por_kilo > 0,
        )
    ) or 0.0

    mercado_avg_kilo = db_session.scalar(
        select(func.avg(Variante.precio_por_kilo))
        .join(Producto, Variante.producto_id == Producto.id)
        .where(
            Producto.activo.is_(True),
            Producto.categoria == "cafe",
            Variante.disponible.is_(True),
            Variante.precio_por_kilo > 0,
        )
    ) or 0.0

    tienda_val = round(float(tienda_avg_kilo), 2)
    mercado_val = round(float(mercado_avg_kilo), 2)
    diff_pct = 0.0
    if mercado_val > 0:
        diff_pct = round(((tienda_val - mercado_val) / mercado_val) * 100, 1)

    if diff_pct < -10:
        posicion = "Muy Económico"
    elif diff_pct < 0:
        posicion = "Competitivo"
    elif diff_pct <= 15:
        posicion = "Estándar de Mercado"
    else:
        posicion = "Segmento Premium"

    origenes_tienda = db_session.execute(
        select(Producto.pais_origen, func.avg(Variante.precio_por_kilo))
        .join(Variante, Variante.producto_id == Producto.id)
        .where(
            Producto.tienda_id == ctx.tienda_id,
            Producto.activo.is_(True),
            Producto.pais_origen.is_not(None),
            Variante.disponible.is_(True),
            Variante.precio_por_kilo > 0,
        )
        .group_by(Producto.pais_origen)
    ).all()

    desglose = []
    for origen, avg_t in origenes_tienda:
        avg_m = db_session.scalar(
            select(func.avg(Variante.precio_por_kilo))
            .join(Producto, Variante.producto_id == Producto.id)
            .where(
                Producto.pais_origen == origen,
                Producto.activo.is_(True),
                Variante.disponible.is_(True),
                Variante.precio_por_kilo > 0,
            )
        ) or avg_t
        t_orig = round(float(avg_t), 2)
        m_orig = round(float(avg_m), 2)
        diff_orig = round(((t_orig - m_orig) / m_orig) * 100, 1) if m_orig > 0 else 0.0
        desglose.append(
            BenchmarkOriginItem(
                origen=origen,
                precio_kilo_promedio_tienda=t_orig,
                precio_kilo_promedio_mercado=m_orig,
                diferencia_porcentaje=diff_orig,
            )
        )

    return StoreBenchmarkResponse(
        precio_kilo_promedio_tienda=tienda_val,
        precio_kilo_promedio_mercado=mercado_val,
        diferencia_porcentaje=diff_pct,
        posicion_mercado=posicion,
        desglose_por_origen=desglose,
    )


@router.get(
    "/analitica/demanda",
    response_model=StoreUnmetDemandResponse,
    summary="Análisis de demanda no cubierta y orígenes populares en búsqueda",
)
def get_store_unmet_demand(
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreUnmetDemandResponse:
    mis_origenes = set(
        db_session.scalars(
            select(Producto.pais_origen)
            .where(
                Producto.tienda_id == ctx.tienda_id,
                Producto.activo.is_(True),
                Producto.pais_origen.is_not(None),
            )
            .distinct()
        ).all()
    )

    top_mercado = db_session.execute(
        select(Producto.pais_origen, func.count(Producto.id).label("total"))
        .where(
            Producto.activo.is_(True),
            Producto.pais_origen.is_not(None),
            Producto.categoria == "cafe",
        )
        .group_by(Producto.pais_origen)
        .order_by(text("total DESC"))
        .limit(8)
    ).all()

    origenes_lista = [{"origen": o, "productos_en_mercado": c} for o, c in top_mercado if o]
    oportunidades = [o for o, _ in top_mercado if o and o not in mis_origenes][:4]

    return StoreUnmetDemandResponse(
        origenes_mas_buscados=origenes_lista,
        oportunidades_catalogo=oportunidades,
    )


# --- DTOs y Endpoints de Moderación de Notas de Cata (Fase 3) ---
class StoreProductNoteItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nota_id: int
    nombre: str
    clave_normalizada: str
    texto_origen: str
    confianza: float
    estado: str
    es_fuera_de_rueda: bool


class StoreProductNotesResponse(BaseModel):
    producto_id: int
    producto_nombre: str
    total_notas: int
    notas: List[StoreProductNoteItem] = Field(default_factory=list)


class StoreNoteActionRequest(BaseModel):
    nota_id: Optional[int] = None
    clave_normalizada: Optional[str] = None


class StoreNoteCreateRequest(BaseModel):
    nombre: Optional[str] = None
    nota: Optional[str] = None

    @model_validator(mode="after")
    def validate_name(self) -> "StoreNoteCreateRequest":
        val = (self.nombre or self.nota or "").strip()
        if len(val) < 2:
            raise ValueError("El nombre de la nota es requerido (mínimo 2 caracteres).")
        self.nombre = val
        return self


@router.get(
    "/productos/{producto_id}/notas",
    response_model=StoreProductNotesResponse,
    summary="Listar notas de cata (confirmadas, sugeridas y fuera de rueda) de un producto",
)
def get_store_product_notes(
    producto_id: int,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> StoreProductNotesResponse:
    prod = db_session.get(Producto, producto_id)
    if not prod or prod.tienda_id != ctx.tienda_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {producto_id} no encontrado en su tienda.",
        )

    relations = db_session.scalars(
        select(ProductoNotaCata)
        .options(selectinload(ProductoNotaCata.nota))
        .where(ProductoNotaCata.producto_id == prod.id)
    ).all()

    items = []
    for r in relations:
        if not r.nota:
            continue
        items.append(
            StoreProductNoteItem(
                nota_id=r.nota.id,
                nombre=r.nota.nombre,
                clave_normalizada=r.nota.clave_normalizada,
                texto_origen=r.texto_origen,
                confianza=r.confianza,
                estado=getattr(r, "estado", "confirmada") or "confirmada",
                es_fuera_de_rueda=bool(getattr(r, "es_fuera_de_rueda", False)),
            )
        )

    return StoreProductNotesResponse(
        producto_id=prod.id,
        producto_nombre=prod.nombre,
        total_notas=len(items),
        notas=items,
    )


@router.post(
    "/productos/{producto_id}/notas/confirmar",
    summary="Confirmar una nota de cata sugerida",
)
def confirm_store_product_note(
    producto_id: int,
    payload: StoreNoteActionRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    prod = db_session.get(Producto, producto_id)
    if not prod or prod.tienda_id != ctx.tienda_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {producto_id} no encontrado en su tienda.",
        )

    query = select(ProductoNotaCata).options(selectinload(ProductoNotaCata.nota)).where(ProductoNotaCata.producto_id == prod.id)
    if payload.nota_id:
        query = query.where(ProductoNotaCata.nota_id == payload.nota_id)
    elif payload.clave_normalizada:
        query = query.join(NotaCata, ProductoNotaCata.nota_id == NotaCata.id).where(NotaCata.clave_normalizada == payload.clave_normalizada)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar nota_id o clave_normalizada.",
        )

    rel = db_session.scalar(query)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada asociada a este producto.",
        )

    estado_previo = rel.estado
    rel.estado = "confirmada"
    rel.confianza = 1.0

    auditoria = AuditoriaAccionesTienda(
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="CONFIRMAR_NOTA_CATA",
        entidad="producto_notas_cata",
        entidad_id=prod.id,
        valores_previos={"nota_id": rel.nota_id, "estado": estado_previo},
        valores_nuevos={"nota_id": rel.nota_id, "estado": "confirmada"},
    )
    db_session.add(auditoria)
    db_session.commit()

    return {
        "exito": True,
        "mensaje": f"Nota '{rel.nota.nombre if rel.nota else rel.nota_id}' confirmada exitosamente.",
        "nota_id": rel.nota_id,
        "estado": "confirmada",
    }


@router.post(
    "/productos/{producto_id}/notas/descartar",
    summary="Descartar una nota de cata sugerida o no deseada",
)
def discard_store_product_note(
    producto_id: int,
    payload: StoreNoteActionRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    prod = db_session.get(Producto, producto_id)
    if not prod or prod.tienda_id != ctx.tienda_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {producto_id} no encontrado en su tienda.",
        )

    query = select(ProductoNotaCata).options(selectinload(ProductoNotaCata.nota)).where(ProductoNotaCata.producto_id == prod.id)
    if payload.nota_id:
        query = query.where(ProductoNotaCata.nota_id == payload.nota_id)
    elif payload.clave_normalizada:
        query = query.join(NotaCata, ProductoNotaCata.nota_id == NotaCata.id).where(NotaCata.clave_normalizada == payload.clave_normalizada)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar nota_id o clave_normalizada.",
        )

    rel = db_session.scalar(query)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada asociada a este producto.",
        )

    estado_previo = rel.estado
    rel.estado = "descartada"

    auditoria = AuditoriaAccionesTienda(
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="DESCARTAR_NOTA_CATA",
        entidad="producto_notas_cata",
        entidad_id=prod.id,
        valores_previos={"nota_id": rel.nota_id, "estado": estado_previo},
        valores_nuevos={"nota_id": rel.nota_id, "estado": "descartada"},
    )
    db_session.add(auditoria)
    db_session.commit()

    return {
        "exito": True,
        "mensaje": f"Nota '{rel.nota.nombre if rel.nota else rel.nota_id}' descartada exitosamente.",
        "nota_id": rel.nota_id,
        "estado": "descartada",
    }


@router.post(
    "/productos/{producto_id}/notas",
    summary="Añadir manualmente una nota de cata confirmada para un producto",
)
def add_store_product_note(
    producto_id: int,
    payload: StoreNoteCreateRequest,
    ctx: StoreAdminContext = Depends(get_current_store_admin),
    db_session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    prod = db_session.get(Producto, producto_id)
    if not prod or prod.tienda_id != ctx.tienda_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {producto_id} no encontrado en su tienda.",
        )

    from core.normalizer import is_valid_tasting_note, SCAFlavorWheelNormalizer, sanitize_text

    nom_limpio = payload.nombre.strip()
    if not is_valid_tasting_note(nom_limpio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El descriptor ingresado no es válido como nota de cata (evite números, encabezados o frases largas).",
        )

    clave = sanitize_text(nom_limpio).replace(" ", "-")
    nota = db_session.scalar(select(NotaCata).where(NotaCata.clave_normalizada == clave))
    if not nota:
        nota = NotaCata(clave_normalizada=clave, nombre=nom_limpio.capitalize())
        db_session.add(nota)
        db_session.flush()

    sca_match = SCAFlavorWheelNormalizer.normalizar_nota(nom_limpio)
    es_fuera = sca_match is None

    rel = db_session.scalar(
        select(ProductoNotaCata).where(
            ProductoNotaCata.producto_id == prod.id,
            ProductoNotaCata.nota_id == nota.id,
        )
    )
    if rel:
        rel.estado = "confirmada"
        rel.confianza = 1.0
    else:
        rel = ProductoNotaCata(
            producto_id=prod.id,
            nota_id=nota.id,
            texto_origen="Agregado manualmente por tostaduría",
            confianza=1.0,
            version_extractor="manual_store_admin",
            estado="confirmada",
            es_fuera_de_rueda=es_fuera,
        )
        db_session.add(rel)

    auditoria = AuditoriaAccionesTienda(
        tienda_id=ctx.tienda_id,
        usuario_id=ctx.usuario_id,
        accion="AGREGAR_NOTA_CATA",
        entidad="producto_notas_cata",
        entidad_id=prod.id,
        valores_previos=None,
        valores_nuevos={"nota_id": nota.id, "nombre": nota.nombre, "es_fuera_de_rueda": es_fuera},
    )
    db_session.add(auditoria)
    db_session.commit()

    return {
        "exito": True,
        "mensaje": f"Nota '{nota.nombre}' agregada y confirmada exitosamente.",
        "nota_id": nota.id,
        "nombre": nota.nombre,
        "clave_normalizada": nota.clave_normalizada,
        "estado": "confirmada",
        "es_fuera_de_rueda": es_fuera,
    }
