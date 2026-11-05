import calendar
from datetime import datetime, date
from typing import Any, Dict, Optional


DEFAULT_FEATURES: Dict[str, bool] = {
    "whatsapp_orders": False,
    "recetas_oficiales": False,
    "radar_demanda": False,
    "benchmark_precios": False,
    "fotos_hd_extra": False,
    "destacado_catalogo": False,
    "publicaciones_novedades": False,
}

VALOR_ESTIMADO_CLIC_CLP: int = 350


def calcular_proxima_fecha_pago(dia_pago: int, hoy: Optional[datetime] = None) -> datetime:
    """Calcula la fecha del próximo vencimiento mensual en base al día de corte acordado.
    
    Ajusta automáticamente al último día de meses más cortos (ej. día 31 en febrero o abril).
    """
    if hoy is None:
        hoy = datetime.now()
        
    dia_clamped = max(1, min(dia_pago, 31))
    year = hoy.year
    month = hoy.month

    def make_date(y: int, m: int, d: int) -> datetime:
        max_d = calendar.monthrange(y, m)[1]
        return datetime(y, m, min(d, max_d), 0, 0, 0)

    candidate = make_date(year, month, dia_clamped)
    if candidate.date() >= hoy.date():
        return candidate
    else:
        if month == 12:
            return make_date(year + 1, 1, dia_clamped)
        else:
            return make_date(year, month + 1, dia_clamped)


def calcular_funcionalidades_efectivas(
    plan_funcionalidades: Optional[Dict[str, bool]] = None,
    override: Optional[Dict[str, bool]] = None
) -> Dict[str, bool]:
    """Combina las funcionalidades base del plan con cualquier override específico de la tienda."""
    resultado = dict(DEFAULT_FEATURES)
    if plan_funcionalidades:
        for k, v in plan_funcionalidades.items():
            resultado[k] = bool(v)
    if override:
        for k, v in override.items():
            resultado[k] = bool(v)
    return resultado


def calcular_balance_roi(
    ventas_whatsapp_clp: int,
    total_pedidos_whatsapp: int,
    clics_salientes: int,
    costo_mensual_clp: int,
) -> Dict[str, Any]:
    """Calcula el balance y ratio de retorno de inversión generado para la tienda."""
    valor_clics = clics_salientes * VALOR_ESTIMADO_CLIC_CLP
    valor_total = ventas_whatsapp_clp + valor_clics
    balance_neto = valor_total - costo_mensual_clp

    if costo_mensual_clp > 0:
        ratio_cobertura = round((valor_total / costo_mensual_clp) * 100, 1)
    else:
        ratio_cobertura = 100.0 if valor_total > 0 else 0.0

    if ratio_cobertura >= 200.0:
        mensaje = f"¡Retorno excepcional! La plataforma generó {ratio_cobertura}% de tu inversión mensual."
    elif ratio_cobertura >= 100.0:
        mensaje = f"Tu plan está 100% cubierto y amortizado con ${valor_total:,} generados este período.".replace(",", ".")
    elif ratio_cobertura > 0.0:
        mensaje = f"El valor generado cubre el {ratio_cobertura}% de tu costo mensual. ¡Sigue potenciando tus ofertas!"
    else:
        mensaje = "Comienza a recibir pedidos y clics para visualizar tu retorno de inversión este mes."

    return {
        "total_pedidos_whatsapp": total_pedidos_whatsapp,
        "monto_ventas_whatsapp_clp": ventas_whatsapp_clp,
        "total_clics_salientes": clics_salientes,
        "valor_estimado_clics_clp": valor_clics,
        "valor_total_generado_clp": valor_total,
        "costo_mensual_suscripcion_clp": costo_mensual_clp,
        "balance_neto_clp": balance_neto,
        "ratio_cobertura_porcentaje": ratio_cobertura,
        "mensaje_retorno": mensaje,
    }

