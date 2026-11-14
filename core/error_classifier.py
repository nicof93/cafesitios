"""
Módulo de clasificación y diagnóstico de fallas de sincronización y conectividad de tiendas.
Permite tipificar errores para generar alertas claras (tienda caída, contraseña activa, etc.).
"""
from typing import Any, Dict, Optional, Union
import re


def extraer_codigo_http(error: Union[Exception, str, None], default: Optional[int] = None) -> Optional[int]:
    """
    Extrae el código numérico de estado HTTP de una excepción, respuesta o mensaje de error.
    Si no hay error, retorna 200. Si no se puede determinar, retorna default (None).
    """
    if error is None:
        return 200

    # 1. Si el objeto tiene response.status_code (como requests.HTTPError)
    response = getattr(error, 'response', None)
    if response is not None:
        status_code = getattr(response, 'status_code', None)
        if isinstance(status_code, int) and 100 <= status_code <= 599:
            return status_code

    # 2. Si el objeto tiene directamente status_code o code
    direct_status = getattr(error, 'status_code', None) or getattr(error, 'code', None)
    if isinstance(direct_status, int) and 100 <= direct_status <= 599:
        return direct_status

    err_str = str(error)

    # 3. Buscar patrones explícitos de códigos HTTP relevantes
    match = re.search(r'\b(200|400|401|403|404|408|429|500|502|503|504)\b', err_str)
    if match:
        return int(match.group(1))

    # 4. Cualquier código HTTP genérico 4xx o 5xx
    match_gen = re.search(r'\b([45]\d{2})\b', err_str)
    if match_gen:
        return int(match_gen.group(1))

    return default


def clasificar_error_sincronizacion(error: Union[Exception, str, None]) -> Dict[str, Any]:
    """
    Clasifica un error de sincronización en códigos estándar legibles:
    - TIENDA_PROTEGIDA_PASSWORD: La tienda tiene contraseña activa (Shopify /password, HTTP 401).
    - SITIO_CAIDO_O_TIMEOUT: Error de conexión, timeout o falla de resolución DNS.
    - ERROR_SERVIDOR_TIENDA: Error 5xx en el hosting/servidor de la tostaduría.
    - CATALOGO_NO_ENCONTRADO: Endpoint no encontrado (HTTP 404).
    - BLOQUEO_BOT_O_RATE_LIMIT: Bloqueo anti-bot perimetral o rate limit (HTTP 403 / 429).
    - CATALOGO_VACIO: La tienda responde pero el catálogo no tiene productos.
    - ERROR_BASE_DATOS: Falla en persistencia SQL o constraints.
    - ERROR_DESCONOCIDO: Otros errores.
    """
    http_code = extraer_codigo_http(error)
    if not error:
        return {
            "codigo": "OK",
            "categoria": "Sincronización Exitosa",
            "icono": "✅",
            "mensaje_amigable": "El catálogo se sincronizó sin errores.",
            "es_error": False,
            "codigo_http": 200,
        }

    err_str = str(error).strip()
    err_lower = err_str.lower()

    # 1. Tienda con página de contraseña o modo privado (/password, HTTP 401 Unauthorized)
    if (
        "401" in err_str
        or "unauthorized" in err_lower
        or "/password" in err_lower
        or "tienda_protegida_password" in err_lower
        or "protegida por contraseña" in err_lower
        or "password page" in err_lower
    ):
        res = {
            "codigo": "TIENDA_PROTEGIDA_PASSWORD",
            "categoria": "Tienda con Contraseña / Modo Mantenimiento",
            "icono": "🔒",
            "mensaje_amigable": "La tienda tiene habilitada la protección por contraseña de Shopify (/password) o requiere autorización. El catálogo está cerrado al público.",
            "es_error": True,
        }

    # 2. Conectividad, DNS, Timeout o Servidor Caído
    elif (
        "timeout" in err_lower
        or "timed out" in err_lower
        or "connection refused" in err_lower
        or "connection reset" in err_lower
        or "failed to resolve" in err_lower
        or "name or service not known" in err_lower
        or "getaddrinfo failed" in err_lower
        or "nodename nor servname provided" in err_lower
        or "max retries exceeded" in err_lower
        or "sitio_caido_o_timeout" in err_lower
        or "no route to host" in err_lower
    ):
        res = {
            "codigo": "SITIO_CAIDO_O_TIMEOUT",
            "categoria": "Sitio Caído o Tiempo de Espera Agotado",
            "icono": "🔌",
            "mensaje_amigable": "No fue posible conectar con el dominio de la tienda. El sitio web no responde, falló el DNS o la conexión expiró por timeout.",
            "es_error": True,
        }

    # 3. Error interno del servidor de la tienda (5xx)
    elif (
        "500" in err_str
        or "502" in err_str
        or "503" in err_str
        or "504" in err_str
        or "bad gateway" in err_lower
        or "service unavailable" in err_lower
        or "gateway timeout" in err_lower
        or "internal server error" in err_lower
    ):
        res = {
            "codigo": "ERROR_SERVIDOR_TIENDA",
            "categoria": "Falla en Servidor de la Tienda (5xx)",
            "icono": "🛑",
            "mensaje_amigable": "El servidor del comercio devolvió un código 5xx (500/502/503/504). La plataforma de la tienda presenta fallas internas temporales.",
            "es_error": True,
        }

    # 4. Catálogo no encontrado (404)
    elif (
        "404" in err_str
        or "not found" in err_lower
        or "catalogo_no_encontrado" in err_lower
        or "no se pudo obtener catálogo en ningún endpoint" in err_lower
    ):
        res = {
            "codigo": "CATALOGO_NO_ENCONTRADO",
            "categoria": "Catálogo No Encontrado (404)",
            "icono": "🔍",
            "mensaje_amigable": "La URL ingresada o los endpoints de catálogo (/products.json, /wp-json/wc/store/products) devolvieron 404 No Encontrado.",
            "es_error": True,
        }

    # 5. Rate limit o bloqueo bot (429 / 403)
    elif (
        "429" in err_str
        or "too many requests" in err_lower
        or "rate limit" in err_lower
        or "403" in err_str
        or "forbidden" in err_lower
        or "cloudflare" in err_lower
    ):
        res = {
            "codigo": "BLOQUEO_BOT_O_RATE_LIMIT",
            "categoria": "Bloqueo Anti-Bot o Límite de Peticiones (429/403)",
            "icono": "🛡️",
            "mensaje_amigable": "El servidor o firewall de la tienda bloqueó las solicitudes automáticas por rate limit o protección Cloudflare.",
            "es_error": True,
        }

    # 6. Catálogo vacío
    elif (
        "catálogo vacío" in err_lower
        or "0 productos devueltos" in err_lower
        or "catalogo vacio" in err_lower
        or "catalogo_vacio" in err_lower
    ):
        res = {
            "codigo": "CATALOGO_VACIO",
            "categoria": "Catálogo Vacío (0 Productos)",
            "icono": "📦",
            "mensaje_amigable": "La conexión fue exitosa pero la colección o catálogo consultado no contiene productos disponibles.",
            "es_error": True,
        }

    # 7. Error de Base de Datos
    elif (
        "stringdatarighttruncation" in err_lower
        or "value too long for type" in err_lower
        or "integrityerror" in err_lower
        or "programmingerror" in err_lower
        or "operationalerror" in err_lower
    ):
        res = {
            "codigo": "ERROR_BASE_DATOS",
            "categoria": "Error de Base de Datos / Persistencia",
            "icono": "💾",
            "mensaje_amigable": "Se extrajeron los productos pero falló la persistencia SQL en la base de datos.",
            "es_error": True,
        }

    # 8. Discrepancia o Validación de Tienda
    elif (
        "cada sincronización debe contener productos de una sola tienda" in err_lower
        or "cada sincronizacion" in err_lower
        or "la tienda activa con id" in err_lower
    ):
        res = {
            "codigo": "ERROR_VALIDACION_TIENDA",
            "categoria": "Discrepancia de Nombre de Tienda",
            "icono": "🏪",
            "mensaje_amigable": "El nombre o identificador de la tienda en el catálogo extraído no coincidía exactamente con el registro de la base de datos.",
            "es_error": True,
        }

    # 9. Desconocido / Otros
    else:
        res = {
            "codigo": "ERROR_DESCONOCIDO",
            "categoria": "Error Desconocido",
            "icono": "⚠️",
            "mensaje_amigable": err_str[:250],
            "es_error": True,
        }

    res["codigo_http"] = http_code
    return res

