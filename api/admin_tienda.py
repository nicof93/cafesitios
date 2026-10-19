from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
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
    Producto,
    Receta,
    Sincronizacion,
    SincronizacionLog,
    Tienda,
    UsuarioTienda,
    Variante,
)
from scrapper_application import sincronizar_tienda

router = APIRouter(prefix="/api/v1/admin/tienda", tags=["Admin Tienda Multi-Inquilino"])


# --- DTOs Pydantic v2 ---
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
    rol: str
    ultima_sincronizacion: Optional[str] = None
    estado_sincronizacion: Optional[str] = None
    total_productos: int = 0
    cooldown_sync_segundos: int = 0
    logo_url: Optional[str] = None


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
    activo: bool
    oculto_catalogo: bool
    variantes: List[StoreProductVariantOutput] = Field(default_factory=list)


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
    if not tienda or not tienda.activo:
        anti_brute_force.record_login_failure(client_ip, identifier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La tostaduría vinculada a esta cuenta está inactiva o no existe.",
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
                activo=bool(p.activo),
                oculto_catalogo=bool(p.oculto_catalogo),
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
        activo=payload.activo,
        oculto_catalogo=payload.oculto_catalogo,
    )
    db_session.add(prod)
    db_session.flush()

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
        activo=bool(prod.activo),
        oculto_catalogo=bool(prod.oculto_catalogo),
        variantes=variantes_dto,
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
    prod.imagen = payload.imagen
    prod.descripcion = payload.descripcion
    prod.pais_origen = payload.origen
    prod.finca = payload.finca
    prod.variedad = payload.variedad
    prod.proceso = payload.proceso
    prod.tueste = payload.tueste
    prod.activo = payload.activo
    prod.oculto_catalogo = payload.oculto_catalogo

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
        activo=bool(prod.activo),
        oculto_catalogo=bool(prod.oculto_catalogo),
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto no existe o no pertenece a tu tostaduría.",
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

