from collections import defaultdict
from datetime import datetime, timedelta
import math
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db_session, require_local_analytics
from api.schemas import (
    MarketAnalyticsResponse,
    MarketDistributionItem,
    MarketStoreDiscountSummary,
    PaginatedSyncHistoryResponse,
    SyncCurrentSummaryResponse,
    SyncHistoryLogItem,
    SyncMetricsSummary,
    SyncNewProductItem,
    SyncPriceChangeItem,
)
from db.database import (
    EstadoSincronizacion,
    HistorialPrecio,
    OfertaTienda,
    Producto,
    Sincronizacion,
    SincronizacionLog,
    Tienda,
    Variante,
)
from domain.search_normalizer import classify_product_category

router = APIRouter(prefix="/api/v1/sync", tags=["Sincronización"])
sincronizacion_router = APIRouter(prefix="/api/v1/sincronizacion", tags=["Sincronización"])
sincronizaciones_router = APIRouter(
    prefix="/api/sincronizaciones",
    tags=["Sincronización y Analítica"],
    dependencies=[Depends(require_local_analytics)],
)
sincronizaciones_v1_router = APIRouter(
    prefix="/api/v1/sincronizaciones",
    tags=["Sincronización y Analítica"],
    dependencies=[Depends(require_local_analytics)],
)
analitica_router = APIRouter(
    prefix="/api/analitica",
    tags=["Analítica de Mercado"],
    dependencies=[Depends(require_local_analytics)],
)
analitica_v1_router = APIRouter(
    prefix="/api/v1/analitica",
    tags=["Analítica de Mercado"],
    dependencies=[Depends(require_local_analytics)],
)


class LastSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    last_sync: Optional[datetime] = None


def _calcular_precio_kilo(precio_clp: int, formato_gramos: int) -> float:
    if precio_clp <= 0 or formato_gramos <= 0:
        return 0.0
    return round((precio_clp / formato_gramos) * 1000, 2)


def _normalizar_tueste(valor: Optional[str]) -> str:
    if not valor or not str(valor).strip():
        return "No especificado"
    limpio = str(valor).strip().lower()
    if "liger" in limpio or "clar" in limpio or "light" in limpio or "filtro" in limpio:
        return "Tueste Claro / Filtro"
    if "medi" in limpio or "omni" in limpio or "medium" in limpio:
        return "Tueste Medio"
    if "oscur" in limpio or "dark" in limpio or "espresso" in limpio or "alto" in limpio:
        return "Tueste Oscuro / Espresso"
    return str(valor).strip().title()[:60]


def _normalizar_proceso(valor: Optional[str]) -> str:
    if not valor or not str(valor).strip():
        return "No especificado"
    limpio = str(valor).strip().lower()
    if "anaer" in limpio or "ferment" in limpio or "carbonic" in limpio or "koji" in limpio or "thermal" in limpio:
        return "Experimental / Fermentado"
    if "honey" in limpio or "miel" in limpio or "melado" in limpio or "pulped" in limpio:
        return "Honey"
    if "natural" in limpio or "seco" in limpio:
        return "Natural"
    if "lavad" in limpio or "washed" in limpio or "humed" in limpio or "húmed" in limpio:
        return "Lavado"
    if "descafein" in limpio or "decaf" in limpio or "swiss" in limpio or "sugarcane" in limpio:
        return "Descafeinado"
    return str(valor).strip().title()[:60]


@sincronizacion_router.get(
    "/ultima",
    response_model=LastSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener la fecha de la última sincronización exitosa",
    description="Retorna la marca temporal de la última sincronización exitosa de productos ejecutada por el scraper.",
)
@sincronizacion_router.get("/last", response_model=LastSyncResponse, include_in_schema=False)
@router.get(
    "/ultima",
    response_model=LastSyncResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/last",
    response_model=LastSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener la fecha de la última sincronización exitosa",
    description="Retorna la marca temporal de la última sincronización exitosa de productos ejecutada por el scraper.",
)
def get_last_sync(db_session: Session = Depends(get_db_session)) -> dict[str, Optional[datetime]]:
    if not hasattr(db_session, "get"):
        return {"last_sync": None}

    estado = db_session.get(EstadoSincronizacion, 1)
    if estado and estado.ultima_ejecucion:
        return {"last_sync": estado.ultima_ejecucion}

    if hasattr(db_session, "scalars"):
        latest_ok_log = db_session.scalars(
            select(SincronizacionLog)
            .where(SincronizacionLog.estado == "OK")
            .order_by(SincronizacionLog.fecha_ejecucion.desc(), SincronizacionLog.id.desc())
            .limit(1)
        ).first()
        if latest_ok_log:
            return {"last_sync": latest_ok_log.fecha_ejecucion}

    return {"last_sync": None}


def get_current_sync_summary(
    db_session: Session = Depends(get_db_session),
) -> SyncCurrentSummaryResponse:
    if not hasattr(db_session, "execute") or not hasattr(db_session, "scalars"):
        return SyncCurrentSummaryResponse()

    latest_log = None
    latest_ok_log = None
    try:
        latest_log = db_session.scalars(
            select(SincronizacionLog)
            .order_by(SincronizacionLog.fecha_ejecucion.desc(), SincronizacionLog.id.desc())
            .limit(1)
        ).first()

        latest_ok_log = db_session.scalars(
            select(SincronizacionLog)
            .where(SincronizacionLog.estado == "OK")
            .order_by(SincronizacionLog.fecha_ejecucion.desc(), SincronizacionLog.id.desc())
            .limit(1)
        ).first()
    except Exception:
        if hasattr(db_session, "rollback"):
            db_session.rollback()

    estado_singleton = db_session.get(EstadoSincronizacion, 1) if hasattr(db_session, "get") else None

    latest_store_sync = db_session.scalars(
        select(Sincronizacion)
        .order_by(Sincronizacion.fecha_inicio.desc(), Sincronizacion.id.desc())
        .limit(1)
    ).first()

    active_product_rows = db_session.execute(
        select(Producto, Tienda)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .where(
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            Tienda.activo.is_(True),
        )
        .order_by(Producto.fecha_creacion.desc(), Producto.id.desc())
    ).all()

    active_variant_rows = db_session.execute(
        select(Variante, Producto, Tienda)
        .join(Producto, Variante.producto_id == Producto.id)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .where(
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            Tienda.activo.is_(True),
        )
        .order_by(Variante.id.asc())
    ).all()

    ofertas_tienda_activas = 0
    try:
        ofertas_tienda_activas = (
            db_session.scalar(
                select(func.count(OfertaTienda.id)).where(OfertaTienda.disponible.is_(True))
            )
            or 0
        )
    except Exception:
        if hasattr(db_session, "rollback"):
            db_session.rollback()

    variantes_disponibles = sum(1 for v, _, _ in active_variant_rows if v.disponible)
    total_ofertas_monitoreadas = max(variantes_disponibles, int(ofertas_tienda_activas))
    total_productos_catalogados = len(active_product_rows)

    variant_ids = [v.id for v, _, _ in active_variant_rows]
    history_by_variant: Dict[int, List[HistorialPrecio]] = defaultdict(list)
    latest_history_ts: Optional[datetime] = None

    if variant_ids:
        history_rows = db_session.scalars(
            select(HistorialPrecio)
            .where(HistorialPrecio.variante_id.in_(variant_ids))
            .order_by(
                HistorialPrecio.variante_id.asc(),
                HistorialPrecio.fecha_registro.desc(),
                HistorialPrecio.id.desc(),
            )
        ).all()
        for h_row in history_rows:
            history_by_variant[h_row.variante_id].append(h_row)
            if h_row.fecha_registro and (latest_history_ts is None or h_row.fecha_registro > latest_history_ts):
                latest_history_ts = h_row.fecha_registro

    cambios_precio: List[SyncPriceChangeItem] = []
    variants_by_product: Dict[int, List[Variante]] = defaultdict(list)

    for variante, producto, tienda in active_variant_rows:
        variants_by_product[producto.id].append(variante)
        hist = history_by_variant.get(variante.id, [])
        formato_g = int(variante.formato_gramos or 250) or 250

        precio_anterior: Optional[int] = None
        precio_nuevo: Optional[int] = None
        pk_anterior: float = 0.0
        pk_nuevo: float = 0.0
        fecha_cambio: Optional[datetime] = None

        if len(hist) >= 2:
            if int(variante.precio_clp) != int(hist[0].precio_clp):
                precio_anterior = int(hist[0].precio_clp)
                precio_nuevo = int(variante.precio_clp)
                pk_anterior = float(hist[0].precio_por_kilo or _calcular_precio_kilo(precio_anterior, formato_g))
                pk_nuevo = float(variante.precio_por_kilo or _calcular_precio_kilo(precio_nuevo, formato_g))
                fecha_cambio = variante.fecha_actualizacion or hist[0].fecha_registro
            else:
                precio_anterior = int(hist[1].precio_clp)
                precio_nuevo = int(hist[0].precio_clp)
                pk_anterior = float(hist[1].precio_por_kilo or _calcular_precio_kilo(precio_anterior, formato_g))
                pk_nuevo = float(hist[0].precio_por_kilo or _calcular_precio_kilo(precio_nuevo, formato_g))
                fecha_cambio = hist[0].fecha_registro
        elif len(hist) == 1 and int(variante.precio_clp) != int(hist[0].precio_clp):
            precio_anterior = int(hist[0].precio_clp)
            precio_nuevo = int(variante.precio_clp)
            pk_anterior = float(hist[0].precio_por_kilo or _calcular_precio_kilo(precio_anterior, formato_g))
            pk_nuevo = float(variante.precio_por_kilo or _calcular_precio_kilo(precio_nuevo, formato_g))
            fecha_cambio = variante.fecha_actualizacion or hist[0].fecha_registro

        if (
            precio_anterior is not None
            and precio_nuevo is not None
            and precio_anterior > 0
            and precio_nuevo > 0
            and precio_nuevo != precio_anterior
        ):
            if pk_anterior <= 0:
                pk_anterior = _calcular_precio_kilo(precio_anterior, formato_g)
            if pk_nuevo <= 0:
                pk_nuevo = _calcular_precio_kilo(precio_nuevo, formato_g)

            diferencia_clp = precio_nuevo - precio_anterior
            porcentaje_variacion = round(((precio_nuevo - precio_anterior) / precio_anterior) * 100, 2)
            diferencia_kilo = round(pk_nuevo - pk_anterior, 2)
            tipo_cambio = "SUBIO" if precio_nuevo > precio_anterior else "BAJO"

            cambios_precio.append(
                SyncPriceChangeItem(
                    id=producto.id,
                    variante_id=variante.id,
                    nombre=producto.nombre,
                    tienda=tienda.nombre,
                    formato_gramos=formato_g,
                    formato=f"{formato_g}g",
                    precio_anterior=precio_anterior,
                    precio_nuevo=precio_nuevo,
                    precio_actual=precio_nuevo,
                    diferencia_clp=diferencia_clp,
                    porcentaje_variacion=porcentaje_variacion,
                    precio_kilo_anterior=round(pk_anterior, 2),
                    precio_kilo_nuevo=round(pk_nuevo, 2),
                    diferencia_kilo_clp=diferencia_kilo,
                    tipo_cambio=tipo_cambio,
                    url_detalle=producto.url_detalle,
                    fecha_cambio=fecha_cambio,
                )
            )

    cambios_precio.sort(key=lambda item: (0 if item.tipo_cambio == "BAJO" else 1, item.diferencia_clp))

    subidas = [c for c in cambios_precio if c.tipo_cambio == "SUBIO"]
    bajadas = [c for c in cambios_precio if c.tipo_cambio == "BAJO"]
    total_subieron = len(subidas)
    total_bajaron = len(bajadas)
    total_cambios = len(cambios_precio)

    porcentaje_variacion_global = (
        round(sum(c.porcentaje_variacion for c in cambios_precio) / total_cambios, 2)
        if total_cambios > 0
        else 0.0
    )
    ahorro_total_clp = sum(abs(c.diferencia_clp) for c in bajadas)
    porcentaje_ahorro_promedio = (
        round(sum(abs(c.porcentaje_variacion) for c in bajadas) / total_bajaron, 2)
        if total_bajaron > 0
        else 0.0
    )

    any_multi_history = any(len(h_list) >= 2 for h_list in history_by_variant.values())
    changed_product_ids = {c.id for c in cambios_precio}

    productos_nuevos_items: List[SyncNewProductItem] = []
    for producto, tienda in active_product_rows:
        prod_variants = variants_by_product.get(producto.id, [])
        if not prod_variants:
            continue
        available_vars = [v for v in prod_variants if v.disponible] or prod_variants
        rep_var = min(available_vars, key=lambda v: (int(v.precio_clp or 0), v.id))
        max_hist_len = max((len(history_by_variant.get(v.id, [])) for v in prod_variants), default=0)

        es_nuevo = False
        if latest_log is not None and latest_log.productos_nuevos == 0 and any_multi_history:
            es_nuevo = False
        elif any_multi_history:
            es_nuevo = max_hist_len <= 1 and producto.id not in changed_product_ids
        else:
            if latest_log is not None and latest_log.productos_nuevos == 0:
                es_nuevo = False
            elif latest_store_sync is not None and latest_store_sync.productos_agregados == 0:
                es_nuevo = False
            else:
                es_nuevo = producto.id not in changed_product_ids

        if es_nuevo:
            formato_g = int(rep_var.formato_gramos or 250) or 250
            precio_clp = int(rep_var.precio_clp or 0)
            pk = float(rep_var.precio_por_kilo or _calcular_precio_kilo(precio_clp, formato_g))
            if pk <= 0 and precio_clp > 0:
                pk = _calcular_precio_kilo(precio_clp, formato_g)
            productos_nuevos_items.append(
                SyncNewProductItem(
                    id=producto.id,
                    nombre=producto.nombre,
                    tienda=tienda.nombre,
                    formato_gramos=formato_g,
                    formato=f"{formato_g}g",
                    precio_clp=precio_clp,
                    precio_por_kilo=round(pk, 2),
                    origen=producto.pais_origen,
                    proceso=producto.proceso,
                    tueste=producto.tueste,
                    url_detalle=producto.url_detalle,
                    imagen=producto.imagen,
                    fecha_creacion=producto.fecha_creacion,
                )
            )

    if latest_log is not None and latest_log.productos_nuevos > 0 and len(productos_nuevos_items) > latest_log.productos_nuevos:
        productos_nuevos_items = productos_nuevos_items[: latest_log.productos_nuevos]

    total_nuevos = (
        int(latest_log.productos_nuevos)
        if (latest_log is not None and latest_log.productos_nuevos > 0 and not productos_nuevos_items)
        else len(productos_nuevos_items)
    )

    ultima_sync: Optional[datetime] = None
    if latest_ok_log and latest_ok_log.fecha_ejecucion:
        ultima_sync = latest_ok_log.fecha_ejecucion
    elif latest_log and latest_log.fecha_ejecucion:
        ultima_sync = latest_log.fecha_ejecucion
    elif estado_singleton and estado_singleton.ultima_ejecucion:
        ultima_sync = estado_singleton.ultima_ejecucion
    elif latest_store_sync:
        ultima_sync = latest_store_sync.fecha_fin or latest_store_sync.fecha_inicio
    elif latest_history_ts:
        ultima_sync = latest_history_ts
    elif active_product_rows:
        ultima_sync = active_product_rows[0][0].fecha_actualizacion or active_product_rows[0][0].fecha_creacion

    estado_actual = "OK"
    if latest_log:
        estado_actual = "OK" if str(latest_log.estado).upper() in ("OK", "EXITOSO") else "ERROR"
    elif latest_store_sync and str(latest_store_sync.resultado).lower() in ("fallido", "error"):
        estado_actual = "ERROR"

    metricas = SyncMetricsSummary(
        total_nuevos=total_nuevos,
        total_subieron_precio=total_subieron,
        total_bajaron_precio=total_bajaron,
        total_cambios_precio=total_cambios,
        porcentaje_variacion_global=porcentaje_variacion_global,
        ahorro_total_clp=ahorro_total_clp,
        porcentaje_ahorro_promedio=porcentaje_ahorro_promedio,
        total_ofertas_monitoreadas=total_ofertas_monitoreadas,
        total_productos_catalogados=total_productos_catalogados,
    )

    return SyncCurrentSummaryResponse(
        fecha_ultima_sincronizacion=ultima_sync,
        ultima_sincronizacion=ultima_sync,
        estado=estado_actual,
        total_nuevos=total_nuevos,
        total_subieron_precio=total_subieron,
        total_bajaron_precio=total_bajaron,
        total_cambios_precio=total_cambios,
        porcentaje_variacion_global=porcentaje_variacion_global,
        ahorro_total_clp=ahorro_total_clp,
        porcentaje_ahorro_promedio=porcentaje_ahorro_promedio,
        total_ofertas_monitoreadas=total_ofertas_monitoreadas,
        total_productos_catalogados=total_productos_catalogados,
        metricas=metricas,
        productos_nuevos=productos_nuevos_items,
        novedades=productos_nuevos_items,
        cambios_precio=cambios_precio,
        productos_cambio_precio=cambios_precio,
    )


def get_sync_history(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db_session: Session = Depends(get_db_session),
) -> PaginatedSyncHistoryResponse:
    if not hasattr(db_session, "execute") or not hasattr(db_session, "scalars"):
        return PaginatedSyncHistoryResponse(page=page, page_size=page_size)

    total_logs = 0
    try:
        total_logs = db_session.scalar(select(func.count(SincronizacionLog.id))) or 0
    except Exception:
        if hasattr(db_session, "rollback"):
            db_session.rollback()
        total_logs = 0
    items: List[SyncHistoryLogItem] = []

    if total_logs > 0:
        total_pages = max(1, math.ceil(total_logs / page_size))
        rows = db_session.scalars(
            select(SincronizacionLog)
            .order_by(SincronizacionLog.fecha_ejecucion.desc(), SincronizacionLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        for row in rows:
            dt = row.fecha_ejecucion
            dur = round(float(row.duracion_segundos or 0.0), 2)
            estado_norm = "OK" if str(row.estado).upper() in ("OK", "EXITOSO", "SUCCESS") else "ERROR"
            items.append(
                SyncHistoryLogItem(
                    id=row.id,
                    fecha_ejecucion=dt,
                    fecha=dt.strftime("%Y-%m-%d"),
                    hora=dt.strftime("%H:%M:%S"),
                    duracion_estimada_segundos=dur,
                    duracion_estimada=f"{dur:.1f}s",
                    estado=estado_norm,
                    productos_nuevos=int(row.productos_nuevos or 0),
                    productos_actualizados=int(row.productos_actualizados or 0),
                    productos_con_cambio_precio=int(row.productos_con_cambio_precio or 0),
                    mensaje_error=row.mensaje_error,
                )
            )
        return PaginatedSyncHistoryResponse(
            page=page,
            page_size=page_size,
            total_items=int(total_logs),
            total_pages=total_pages,
            items=items,
            data=items,
            historial=items,
        )

    total_syncs = db_session.scalar(select(func.count(Sincronizacion.id))) or 0
    total_pages = max(1, math.ceil(total_syncs / page_size)) if total_syncs > 0 else 1

    if total_syncs > 0:
        sync_rows = db_session.scalars(
            select(Sincronizacion)
            .order_by(Sincronizacion.fecha_inicio.desc(), Sincronizacion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        for row in sync_rows:
            dt = row.fecha_fin or row.fecha_inicio
            dur = 0.0
            if row.fecha_fin and row.fecha_inicio:
                try:
                    dur = max(0.0, round((row.fecha_fin - row.fecha_inicio).total_seconds(), 2))
                except Exception:
                    dur = 0.0
            estado_norm = "OK" if str(row.resultado).lower() in ("ok", "exitoso", "success") else "ERROR"
            items.append(
                SyncHistoryLogItem(
                    id=row.id,
                    fecha_ejecucion=dt,
                    fecha=dt.strftime("%Y-%m-%d"),
                    hora=dt.strftime("%H:%M:%S"),
                    duracion_estimada_segundos=dur,
                    duracion_estimada=f"{dur:.1f}s",
                    estado=estado_norm,
                    productos_nuevos=int(row.productos_agregados or 0),
                    productos_actualizados=int(row.productos_actualizados or 0),
                    productos_con_cambio_precio=0,
                    mensaje_error=row.detalle_error,
                )
            )

    return PaginatedSyncHistoryResponse(
        page=page,
        page_size=page_size,
        total_items=int(total_syncs),
        total_pages=total_pages,
        items=items,
        data=items,
        historial=items,
    )


def get_market_analytics(
    db_session: Session = Depends(get_db_session),
) -> MarketAnalyticsResponse:
    if not hasattr(db_session, "execute") or not hasattr(db_session, "scalars"):
        return MarketAnalyticsResponse()

    all_rows = db_session.execute(
        select(Variante, Producto, Tienda)
        .join(Producto, Variante.producto_id == Producto.id)
        .join(Tienda, Producto.tienda_id == Tienda.id)
        .where(
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            Tienda.activo.is_(True),
            Variante.disponible.is_(True),
        )
    ).all()

    if not all_rows:
        return MarketAnalyticsResponse()

    coffee_rows = [
        (v, p, t)
        for v, p, t in all_rows
        if classify_product_category(p.nombre) == "cafe"
    ]
    rows_to_analyze = coffee_rows if coffee_rows else all_rows

    precios_kilo: List[float] = []
    precios_bolsa: List[int] = []
    store_ids = set()

    store_products: Dict[str, set] = defaultdict(set)
    store_kilo_prices: Dict[str, List[float]] = defaultdict(list)
    store_discounts: Dict[str, List[float]] = defaultdict(list)

    tueste_products: Dict[str, set] = defaultdict(set)
    tueste_kilo_prices: Dict[str, List[float]] = defaultdict(list)
    proceso_products: Dict[str, set] = defaultdict(set)
    proceso_kilo_prices: Dict[str, List[float]] = defaultdict(list)

    for variante, producto, tienda in rows_to_analyze:
        formato_g = int(variante.formato_gramos or 250) or 250
        precio_clp = int(variante.precio_clp or 0)
        precio_orig = int(variante.precio_original_clp or precio_clp)
        pk = float(variante.precio_por_kilo or _calcular_precio_kilo(precio_clp, formato_g))
        if pk <= 0 and precio_clp > 0:
            pk = _calcular_precio_kilo(precio_clp, formato_g)

        if precio_clp > 0:
            precios_bolsa.append(precio_clp)
        if pk > 0:
            precios_kilo.append(pk)
            store_kilo_prices[tienda.nombre].append(pk)

        store_ids.add(tienda.id)
        store_products[tienda.nombre].add(producto.id)

        desc_pct = 0.0
        if variante.descuento_porcentaje and int(variante.descuento_porcentaje) > 0:
            desc_pct = float(variante.descuento_porcentaje)
        elif precio_orig > precio_clp > 0:
            desc_pct = round(((precio_orig - precio_clp) / precio_orig) * 100, 2)

        if desc_pct > 0 or bool(variante.en_oferta):
            store_discounts[tienda.nombre].append(desc_pct if desc_pct > 0 else 5.0)

        cat_tueste = _normalizar_tueste(producto.tueste)
        tueste_products[cat_tueste].add(producto.id)
        if pk > 0:
            tueste_kilo_prices[cat_tueste].append(pk)

        cat_proceso = _normalizar_proceso(producto.proceso)
        proceso_products[cat_proceso].add(producto.id)
        if pk > 0:
            proceso_kilo_prices[cat_proceso].append(pk)

    precio_promedio_kilo = round(sum(precios_kilo) / len(precios_kilo), 2) if precios_kilo else 0.0
    precio_minimo_kilo = round(min(precios_kilo), 2) if precios_kilo else 0.0
    precio_maximo_kilo = round(max(precios_kilo), 2) if precios_kilo else 0.0
    precio_promedio_bolsa = int(round(sum(precios_bolsa) / len(precios_bolsa))) if precios_bolsa else 0

    store_summaries: List[MarketStoreDiscountSummary] = []
    for store_name, prod_set in store_products.items():
        k_prices = store_kilo_prices.get(store_name, [])
        d_list = store_discounts.get(store_name, [])
        avg_kilo = round(sum(k_prices) / len(k_prices), 2) if k_prices else 0.0
        avg_desc = round(sum(d_list) / len(d_list), 2) if d_list else 0.0
        store_summaries.append(
            MarketStoreDiscountSummary(
                nombre=store_name,
                descuento_promedio_porcentaje=avg_desc,
                total_ofertas_descuento=len(d_list),
                precio_promedio_kilo=avg_kilo,
                cantidad_productos=len(prod_set),
            )
        )

    if store_summaries:
        mejor_descuento_store = max(
            store_summaries,
            key=lambda s: (
                s.descuento_promedio_porcentaje,
                s.total_ofertas_descuento,
                -s.precio_promedio_kilo if s.precio_promedio_kilo > 0 else 0.0,
            ),
        )
    else:
        mejor_descuento_store = MarketStoreDiscountSummary()

    tiendas_competitivas = sorted(
        store_summaries,
        key=lambda s: (
            s.precio_promedio_kilo if s.precio_promedio_kilo > 0 else float("inf"),
            -s.descuento_promedio_porcentaje,
        ),
    )

    total_unique_products = max(1, len({p.id for _, p, _ in rows_to_analyze}))

    distribucion_tueste: List[MarketDistributionItem] = []
    for cat, prod_ids in tueste_products.items():
        k_list = tueste_kilo_prices.get(cat, [])
        cnt = len(prod_ids)
        distribucion_tueste.append(
            MarketDistributionItem(
                categoria=cat,
                cantidad=cnt,
                porcentaje=round((cnt / total_unique_products) * 100, 2),
                precio_promedio_kilo=round(sum(k_list) / len(k_list), 2) if k_list else 0.0,
            )
        )
    distribucion_tueste.sort(key=lambda item: (-item.cantidad, item.categoria))

    distribucion_proceso: List[MarketDistributionItem] = []
    for cat, prod_ids in proceso_products.items():
        k_list = proceso_kilo_prices.get(cat, [])
        cnt = len(prod_ids)
        distribucion_proceso.append(
            MarketDistributionItem(
                categoria=cat,
                cantidad=cnt,
                porcentaje=round((cnt / total_unique_products) * 100, 2),
                precio_promedio_kilo=round(sum(k_list) / len(k_list), 2) if k_list else 0.0,
            )
        )
    distribucion_proceso.sort(key=lambda item: (-item.cantidad, item.categoria))

    return MarketAnalyticsResponse(
        precio_promedio_kilo=precio_promedio_kilo,
        precio_minimo_kilo=precio_minimo_kilo,
        precio_maximo_kilo=precio_maximo_kilo,
        precio_promedio_bolsa_clp=precio_promedio_bolsa,
        total_variantes_analizadas=len(rows_to_analyze),
        total_tiendas_activas=len(store_ids),
        tienda_mejor_descuento=mejor_descuento_store,
        tiendas_mas_competitivas=tiendas_competitivas,
        distribucion_tueste=distribucion_tueste,
        distribucion_proceso=distribucion_proceso,
    )


for _sync_r in (sincronizaciones_router, sincronizaciones_v1_router):
    _sync_r.add_api_route(
        "/resumen-actual",
        get_current_sync_summary,
        methods=["GET"],
        response_model=SyncCurrentSummaryResponse,
        status_code=status.HTTP_200_OK,
        summary="Resumen actual de sincronización y variaciones de precio",
        description="Retorna la fecha/hora de la última sincronización, métricas agregadas, productos nuevos y variaciones de precio.",
    )
    _sync_r.add_api_route(
        "/historial",
        get_sync_history,
        methods=["GET"],
        response_model=PaginatedSyncHistoryResponse,
        status_code=status.HTTP_200_OK,
        summary="Historial paginado de ejecuciones de sincronización",
        description="Retorna el listado paginado de logs de ejecución con fecha, hora, duración estimada, estado y conteos.",
    )

for _ana_r in (analitica_router, analitica_v1_router):
    _ana_r.add_api_route(
        "/mercado",
        get_market_analytics,
        methods=["GET"],
        response_model=MarketAnalyticsResponse,
        status_code=status.HTTP_200_OK,
        summary="Analítica y estadísticas globales del mercado de café",
        description="Retorna el precio promedio por kilo, tienda con mejor descuento promedio y distribución por nivel de tueste y proceso.",
    )

# Endpoints canónicos en español (/api/v1/sincronizacion)
sincronizacion_router.add_api_route(
    "/resumen",
    get_current_sync_summary,
    methods=["GET"],
    response_model=SyncCurrentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Resumen de la última sincronización y variaciones de precio",
    description="Retorna la fecha/hora de la última sincronización, métricas agregadas, productos nuevos y variaciones de precio.",
)
sincronizacion_router.add_api_route(
    "/resumen-actual",
    get_current_sync_summary,
    methods=["GET"],
    response_model=SyncCurrentSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
sincronizacion_router.add_api_route(
    "/historial",
    get_sync_history,
    methods=["GET"],
    response_model=PaginatedSyncHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Historial paginado de ejecuciones de sincronización",
    description="Retorna el listado paginado de logs de ejecución con fecha, hora, duración estimada, estado y conteos.",
)
sincronizacion_router.add_api_route(
    "/mercado",
    get_market_analytics,
    methods=["GET"],
    response_model=MarketAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Analítica y estadísticas globales del mercado de café",
    description="Retorna el precio promedio por kilo, tienda con mejor descuento promedio y distribución por nivel de tueste y proceso.",
)

# Endpoints canónicos y alias en inglés (/api/v1/sync)
router.add_api_route(
    "/summary",
    get_current_sync_summary,
    methods=["GET"],
    response_model=SyncCurrentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Current sync summary and price variations",
    description="Returns latest sync time, aggregate metrics, new products and price changes.",
)
router.add_api_route(
    "/resumen",
    get_current_sync_summary,
    methods=["GET"],
    response_model=SyncCurrentSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
router.add_api_route(
    "/resumen-actual",
    get_current_sync_summary,
    methods=["GET"],
    response_model=SyncCurrentSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
router.add_api_route(
    "/history",
    get_sync_history,
    methods=["GET"],
    response_model=PaginatedSyncHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Paginated sync execution logs history",
    description="Returns list of execution logs.",
)
router.add_api_route(
    "/historial",
    get_sync_history,
    methods=["GET"],
    response_model=PaginatedSyncHistoryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
router.add_api_route(
    "/market",
    get_market_analytics,
    methods=["GET"],
    response_model=MarketAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Coffee market global analytics and statistics",
    description="Returns average price per kg, best store discounts, and roasting/process distribution.",
)
router.add_api_route(
    "/mercado",
    get_market_analytics,
    methods=["GET"],
    response_model=MarketAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
