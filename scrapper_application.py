import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from api.stores import extract_official_website
from db.database import DatabaseManager
from scrapper.coffee_metadata import (
    extract_coffee_characteristics,
    summarize_extraction_coverage,
    generar_resumen_corto,
)
import logging
from core.extractor import CoffeeAttributesExtractor
from core.error_classifier import clasificar_error_sincronizacion
from core.store_news_helper import sincronizar_novedad_nueva_tienda
from scrapper.driver_factory import DriverFactory
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver
from scrapper.jumpseller_driver import JumpsellerDriver
from scrapper.prestashop_driver import PrestaShopDriver
from scrapper.odoo_driver import OdooDriver
from scrapper.sumup_driver import SumUpDriver

drivers_por_plataforma = dict(DriverFactory._drivers)


def consumir_productos_tienda(tienda: Dict[str, Any]) -> List[Dict[str, Any]]:
    plataforma = (tienda.get('plataforma') or '').strip().lower()
    if plataforma in drivers_por_plataforma:
        primary_driver = drivers_por_plataforma[plataforma]
        driver_classes = [primary_driver] + [
            cls for name, cls in drivers_por_plataforma.items() if name != plataforma
        ]
    elif plataforma in ('', 'desconocida'):
        driver_classes = list(drivers_por_plataforma.values())
    else:
        raise ValueError(f"Plataforma no soportada: {tienda['plataforma']}")

    # Extraer URLs de catálogos si la tienda tiene múltiples colecciones
    catalogos = tienda.get('catalogos') or []
    urls_catalogos: List[str] = [
        c['url_catalogo']
        for c in catalogos
        if isinstance(c, dict) and c.get('activa', True) and c.get('url_catalogo')
    ]
    if not urls_catalogos:
        url_base = tienda.get('url_base')
        if url_base:
            urls_catalogos = [url_base]

    if not urls_catalogos:
        return []

    productos_por_clave: Dict[str, Dict[str, Any]] = {}
    errores_totales: List[str] = []
    catalogos_exitosos = 0

    for url_cat in urls_catalogos:
        productos_url = None
        errores = []
        for driver_class in driver_classes:
            driver = driver_class(nombre=tienda['nombre'], url_base=url_cat)
            try:
                productos_url = driver.consumir_productos()
                if productos_url is not None:
                    catalogos_exitosos += 1
                    break
            except Exception as error:
                err_msg = f"{driver_class.__name__}: {error}"
                errores.append(err_msg)
                errores_totales.append(err_msg)
                # Si el error es 429 (Rate Limit), detener inmediatamente y propagar como error de tienda
                if "429" in str(error) or "too many requests" in str(error).lower() or "rate limit" in str(error).lower():
                    raise RuntimeError(f"HTTP 429 Too Many Requests: Rate limit alcanzado en '{tienda['nombre']}' ({url_cat})")

        if productos_url is None:
            if len(urls_catalogos) == 1:
                raise RuntimeError(
                    f"No se pudo detectar una plataforma válida para '{tienda['nombre']}' en {url_cat}: "
                    + '; '.join(errores)
                )
            else:
                logging.warning(
                    f"[{tienda['nombre']}] Falló consumo de catálogo {url_cat}: {'; '.join(errores)}"
                )
                continue

        # Deduplicar productos y combinar variantes entre colecciones
        for p in productos_url:
            clave = p.get('url_detalle') or p.get('id_externo') or p.get('nombre')
            if not clave:
                continue

            if clave not in productos_por_clave:
                productos_por_clave[clave] = p
            else:
                existente = productos_por_clave[clave]
                variantes_existentes = existente.setdefault('variantes', [])
                ids_vars_existentes = {
                    v.get('id_variante_externo') or (v.get('formato_gramos'), v.get('opcion'))
                    for v in variantes_existentes
                }
                for nueva_var in p.get('variantes', []):
                    var_key = nueva_var.get('id_variante_externo') or (
                        nueva_var.get('formato_gramos'),
                        nueva_var.get('opcion'),
                    )
                    if var_key not in ids_vars_existentes:
                        variantes_existentes.append(nueva_var)
                        ids_vars_existentes.add(var_key)

                if not existente.get('imagen') and p.get('imagen'):
                    existente['imagen'] = p.get('imagen')
                if not existente.get('descripcion') and p.get('descripcion'):
                    existente['descripcion'] = p.get('descripcion')

    if not productos_por_clave and urls_catalogos and catalogos_exitosos == 0 and errores_totales:
        raise RuntimeError(
            f"No se pudo sincronizar ningún catálogo de '{tienda['nombre']}': {'; '.join(errores_totales)}"
        )

    return list(productos_por_clave.values())


def sincronizar_tienda(
    tienda: Any,
    db: Any = None,
    extractor: Any = None,
    ip_origen: Optional[str] = None,
) -> dict:
    import time
    inicio = time.monotonic()
    if db is None:
        db = DatabaseManager()
    if extractor is None:
        extractor = CoffeeAttributesExtractor()

    if isinstance(tienda, int):
        tienda_dict = db.obtener_tienda_por_id(tienda)
        if not tienda_dict:
            return {
                "tienda_id": tienda,
                "nombre": f"Tienda #{tienda}",
                "exito": False,
                "total_productos": 0,
                "productos_nuevos": 0,
                "productos_actualizados": 0,
                "productos_eliminados": 0,
                "duracion_segundos": 0.0,
                "error": f"La tienda con ID {tienda} no existe en la base de datos.",
                "codigo_http": 404,
                "ip_origen": ip_origen,
            }
        tienda = tienda_dict

    tienda_id = tienda['id']
    nombre_tienda = tienda.get('nombre', f"Tienda #{tienda_id}")

    # Resolución y persistencia de favicon/logo de la tienda si no está resuelto
    if not tienda.get('logo_url'):
        sitio_oficial = extract_official_website(tienda.get('url_base'))
        if sitio_oficial:
            try:
                domain = urlparse(sitio_oficial).netloc
                if domain:
                    favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                    db.actualizar_logo_tienda(tienda_id, favicon_url)
                    tienda['logo_url'] = favicon_url
            except Exception:
                pass

    sincronizacion_id = None
    try:
        sincronizacion_id = db.iniciar_sincronizacion(tienda_id, ip_origen=ip_origen)
        productos = consumir_productos_tienda(tienda)
        catalogo_cascada = []

        for producto in productos:
            producto['caracteristicas_cafe'] = extract_coffee_characteristics(
                producto.get('descripcion'),
                title=producto.get('nombre'),
            )
            atributos = extractor.extract(
                producto.get('descripcion'),
                nombre_producto=producto.get('nombre')
            )
            if atributos.get('puntuacion_sca'):
                producto['caracteristicas_cafe']['puntuacion_sca'] = atributos.get('puntuacion_sca')
            if atributos.get('tueste'):
                producto['caracteristicas_cafe']['tueste'] = atributos.get('tueste')
            elif producto.get('tueste'):
                atributos['tueste'] = producto.get('tueste')
                producto['caracteristicas_cafe']['tueste'] = producto.get('tueste')

            if atributos.get('escala_agtron'):
                producto['caracteristicas_cafe']['escala_agtron'] = atributos.get('escala_agtron')

            if atributos.get('origen') and not producto['caracteristicas_cafe'].get('pais_origen'):
                producto['caracteristicas_cafe']['pais_origen'] = atributos.get('origen')

            if not atributos.get('proceso') and producto.get('proceso'):
                atributos['proceso'] = producto.get('proceso')
                producto['caracteristicas_cafe']['proceso'] = producto.get('proceso')

            if producto.get('notas_cata'):
                notas_existentes = set(atributos.get('notas_cata', []))
                notas_agregadas = False
                for n in producto.get('notas_cata', []):
                    if n and n not in notas_existentes:
                        atributos['notas_cata'].append(n)
                        notas_agregadas = True
                if notas_agregadas:
                    from core.normalizer import SCAFlavorWheelNormalizer
                    clasif = SCAFlavorWheelNormalizer.clasificar_notas(atributos['notas_cata'])
                    atributos['notas_normalizadas'] = clasif['notas_normalizadas']
                    atributos['macro_familias'] = clasif['macro_familias']

            resumen = generar_resumen_corto(
                titulo=producto.get('nombre'),
                descripcion=producto.get('descripcion'),
                notas=atributos.get('notas_cata') or producto.get('notas_cata'),
                proceso=producto['caracteristicas_cafe'].get('proceso') or atributos.get('proceso'),
                origen=producto['caracteristicas_cafe'].get('pais_origen') or atributos.get('origen'),
                variedad=producto['caracteristicas_cafe'].get('variedad') or atributos.get('variedad'),
            )
            producto['caracteristicas_cafe']['resumen_corto'] = resumen
            producto['descripcion_resumida'] = resumen

            ofertas = []
            for var in producto.get('variantes', []):
                ofertas.append({
                    'precio_actual': var.get('precio_clp', 0),
                    'formato_gramos': var.get('formato_gramos', 250),
                    'precio_por_kilo': var.get('precio_por_kilo', 0.0),
                    'es_estimado': False if var.get('formato_gramos') == 1000 else var.get('es_estimado', True),
                    'link_detalle': f"{producto.get('url_detalle')}?variant={var.get('id_variante_externo')}",
                    'disponible': var.get('disponible', True),
                })

            catalogo_cascada.append({
                'nombre': producto.get('nombre'),
                'origen': atributos.get('origen'),
                'finca_productor': atributos.get('finca_productor'),
                'variedad': atributos.get('variedad'),
                'proceso': atributos.get('proceso'),
                'lote': atributos.get('lote'),
                'notas_cata': atributos.get('notas_cata', []),
                'notas_normalizadas': atributos.get('notas_normalizadas', []),
                'hash_descripcion': atributos.get('hash_descripcion'),
                'ofertas': ofertas,
            })

        conteos = db.guardar_catalogo(productos, tienda_id=tienda_id)
        db.guardar_cafes_cascada(catalogo_cascada, tienda_id=tienda_id)

        db.finalizar_sincronizacion(sincronizacion_id, 'exitoso', **{
            'productos_agregados': conteos['agregados'],
            'productos_eliminados': conteos['eliminados'],
            'productos_actualizados': conteos['actualizados'],
            'codigo_http': 200,
            'ip_origen': ip_origen,
        })

        try:
            with db.SessionLocal() as news_session:
                sincronizar_novedad_nueva_tienda(tienda_id, news_session)
                news_session.commit()
        except Exception as e_news:
            logging.warning(f"No se pudo sincronizar novedad de bienvenida para tienda {tienda_id}: {e_news}")

        duracion = round(time.monotonic() - inicio, 2)
        return {
            "tienda_id": tienda_id,
            "nombre": nombre_tienda,
            "exito": True,
            "total_productos": len(productos),
            "productos_nuevos": conteos.get('agregados', 0),
            "productos_actualizados": conteos.get('actualizados', 0),
            "productos_eliminados": conteos.get('eliminados', 0),
            "duracion_segundos": duracion,
            "error": None,
            "codigo_error": "OK",
            "categoria_error": None,
            "mensaje_amigable": None,
            "codigo_http": 200,
            "ip_origen": ip_origen,
        }
    except Exception as error:
        duracion = round(time.monotonic() - inicio, 2)
        diag = clasificar_error_sincronizacion(error)
        codigo_http = diag.get("codigo_http")
        detalle_err = f"[{diag['codigo']}]" + (f" [HTTP {codigo_http}]" if codigo_http else "") + f" {str(error)}"
        if sincronizacion_id is not None:
            try:
                db.finalizar_sincronizacion(
                    sincronizacion_id,
                    'fallido',
                    detalle_error=detalle_err,
                    codigo_http=codigo_http,
                    ip_origen=ip_origen,
                )
            except Exception:
                pass
        return {
            "tienda_id": tienda_id,
            "nombre": nombre_tienda,
            "exito": False,
            "total_productos": 0,
            "productos_nuevos": 0,
            "productos_actualizados": 0,
            "productos_eliminados": 0,
            "duracion_segundos": duracion,
            "error": str(error),
            "codigo_error": diag["codigo"],
            "categoria_error": diag["categoria"],
            "mensaje_amigable": diag["mensaje_amigable"],
            "codigo_http": codigo_http,
            "ip_origen": ip_origen,
        }


def obtener_diagnostico_red() -> Dict[str, Any]:
    """
    Obtiene la IP pública del host/runner y los encabezados HTTP base que se utilizarán
    para las conexiones salientes de scraping para trazabilidad y diagnóstico de rate-limiting.
    """
    import json
    import urllib.request
    ip_detectada = "No detectada / Offline"
    endpoints = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/all.json",
        "https://icanhazip.com",
    ]
    for ep in endpoints:
        try:
            req = urllib.request.Request(
                ep,
                headers={"User-Agent": "curl/7.68.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode('utf-8', errors='ignore').strip()
                if raw.startswith('{'):
                    try:
                        data = json.loads(raw)
                        ip_detectada = data.get("ip") or data.get("ip_addr") or raw
                        break
                    except Exception:
                        pass
                elif raw:
                    ip_detectada = raw
                    break
        except Exception:
            continue

    headers_base = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html;q=0.9, */*;q=0.8',
        'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
    }
    return {
        "ip_publica": ip_detectada,
        "headers": headers_base,
    }


def sincronizar_multiples_tiendas(
    tiendas: list,
    db: Any = None,
    extractor: Any = None,
    max_workers: Optional[int] = None,
    registrar_log_global: bool = True,
) -> dict:
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if max_workers is None:
        try:
            max_workers = int(os.getenv("SCRAPER_CONCURRENCY", "4"))
        except (ValueError, TypeError):
            max_workers = 4

    inicio_corrida = time.monotonic()
    if db is None:
        db = DatabaseManager()
    if extractor is None:
        extractor = CoffeeAttributesExtractor()

    # Diagnóstico de Red e Identidad Saliente
    diag_red = obtener_diagnostico_red()
    ip_saliente = diag_red.get('ip_publica')
    print("\n" + "=" * 70)
    print(f"🌐 [DIAGNÓSTICO RED] IP Pública Saliente: {ip_saliente}")
    print(f"📡 [DIAGNÓSTICO RED] Headers HTTP Base:   {diag_red['headers']}")
    print(f"⚙️  [CONCURRENCIA] Hilos de ejecución:     {max_workers} workers")
    print("=" * 70 + "\n")
    logging.info(f"[RED] IP: {ip_saliente} | Headers: {diag_red['headers']} | Workers: {max_workers}")

    detalles = []
    total_nuevos = 0
    total_actualizados = 0
    total_eliminados = 0
    total_productos_sincronizados = 0
    tiendas_exitosas = 0
    tiendas_fallidas = 0

    if max_workers <= 1 or len(tiendas) <= 1:
        for tienda in tiendas:
            res = sincronizar_tienda(tienda, db=db, extractor=extractor, ip_origen=ip_saliente)
            detalles.append(res)
            if res['exito']:
                tiendas_exitosas += 1
                total_nuevos += res.get('productos_nuevos', 0)
                total_actualizados += res.get('productos_actualizados', 0)
                total_eliminados += res.get('productos_eliminados', 0)
                total_productos_sincronizados += res.get('total_productos', 0)
                print(f"✅ {res['nombre']} [HTTP {res.get('codigo_http', 200)}]: {res['total_productos']} productos sincronizados ({res['productos_nuevos']} nuevos, {res['productos_actualizados']} actualizados) en {res.get('duracion_segundos', 0)}s.")
            else:
                tiendas_fallidas += 1
                c_http = res.get('codigo_http')
                c_http_str = f" [HTTP {c_http}]" if c_http else ""
                if res.get('codigo_error') == 'BLOQUEO_BOT_O_RATE_LIMIT' or '429' in str(res.get('error', '')):
                    print(f"⛔ [RATE LIMIT 429]{c_http_str} {res['nombre']}: {res['error']} ({res.get('mensaje_amigable')})")
                else:
                    print(f"❌{c_http_str} {res['nombre']}: {res['error']}")
    else:
        timeout_tienda = int(os.getenv("SCRAPER_STORE_TIMEOUT", "60"))
        print(f"⚡ Procesando {len(tiendas)} tiendas de forma concurrente con {max_workers} hilos (timeout por tienda: {timeout_tienda}s)...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_store = {
                executor.submit(sincronizar_tienda, tienda, db, extractor, ip_saliente): tienda
                for tienda in tiendas
            }
            for future in as_completed(future_to_store):
                try:
                    res = future.result(timeout=timeout_tienda)
                except (TimeoutError, Exception) as e:
                    t_info = future_to_store[future]
                    t_id = t_info.get("id") if isinstance(t_info, dict) else t_info
                    t_nombre = t_info.get("nombre") if isinstance(t_info, dict) else f"Tienda #{t_id}"
                    es_timeout = isinstance(e, TimeoutError) or "timeout" in str(e).lower()
                    diag = clasificar_error_sincronizacion("timeout" if es_timeout else e)
                    codigo_http = 408 if es_timeout else diag.get("codigo_http")
                    error_msg = f"Tiempo de espera agotado ({timeout_tienda}s) al sincronizar tienda" if es_timeout else str(e)
                    res = {
                        "tienda_id": t_id,
                        "nombre": t_nombre,
                        "exito": False,
                        "total_productos": 0,
                        "productos_nuevos": 0,
                        "productos_actualizados": 0,
                        "productos_eliminados": 0,
                        "duracion_segundos": float(timeout_tienda) if es_timeout else 0.0,
                        "error": error_msg,
                        "codigo_error": diag["codigo"],
                        "categoria_error": diag["categoria"],
                        "mensaje_amigable": (
                            f"La sincronización de '{t_nombre}' superó el tiempo límite de {timeout_tienda}s y fue cancelada para continuar con las demás tiendas."
                            if es_timeout
                            else diag["mensaje_amigable"]
                        ),
                        "codigo_http": codigo_http,
                        "ip_origen": ip_saliente,
                    }

                detalles.append(res)
                if res['exito']:
                    tiendas_exitosas += 1
                    total_nuevos += res.get('productos_nuevos', 0)
                    total_actualizados += res.get('productos_actualizados', 0)
                    total_eliminados += res.get('productos_eliminados', 0)
                    total_productos_sincronizados += res.get('total_productos', 0)
                    print(f"✅ {res['nombre']} [HTTP {res.get('codigo_http', 200)}]: {res['total_productos']} productos sincronizados ({res['productos_nuevos']} nuevos, {res['productos_actualizados']} actualizados) en {res.get('duracion_segundos', 0)}s.")
                else:
                    tiendas_fallidas += 1
                    c_http = res.get('codigo_http')
                    c_http_str = f" [HTTP {c_http}]" if c_http else ""
                    if res.get('codigo_error') == 'BLOQUEO_BOT_O_RATE_LIMIT' or '429' in str(res.get('error', '')):
                        print(f"⛔ [RATE LIMIT 429]{c_http_str} {res['nombre']}: {res['error']} ({res.get('mensaje_amigable')})")
                    else:
                        print(f"❌{c_http_str} {res['nombre']}: {res['error']}")

    duracion_total = round(time.monotonic() - inicio_corrida, 2)
    db.registrar_ultima_sincronizacion()
    if hasattr(db, 'refrescar_vistas_materializadas'):
        try:
            db.refrescar_vistas_materializadas()
        except Exception:
            pass

    # Resumen y agregación de códigos HTTP de respuesta
    resumen_codigos: Dict[str, int] = {}
    for d in detalles:
        code_key = str(d.get("codigo_http") or ("200" if d.get("exito") else "ERROR"))
        resumen_codigos[code_key] = resumen_codigos.get(code_key, 0) + 1

    if registrar_log_global and hasattr(db, 'registrar_sincronizacion_log'):
        estado_global = 'OK' if (tiendas_exitosas > 0 or not tiendas) else 'ERROR'
        errores_msg = '; '.join([f"{d['nombre']}: {d['error']}" for d in detalles if not d['exito']]) or None
        try:
            db.registrar_sincronizacion_log(
                estado=estado_global,
                productos_nuevos=total_nuevos,
                productos_actualizados=total_actualizados,
                productos_con_cambio_precio=0,
                duracion_segundos=duracion_total,
                mensaje_error=errores_msg,
                ip_origen=ip_saliente,
                resumen_codigos=resumen_codigos,
            )
        except Exception:
            pass

    return {
        'total_tiendas': len(tiendas),
        'tiendas_exitosas': tiendas_exitosas,
        'tiendas_fallidas': tiendas_fallidas,
        'total_productos_sincronizados': total_productos_sincronizados,
        'total_productos_nuevos': total_nuevos,
        'total_productos_actualizados': total_actualizados,
        'total_productos_eliminados': total_eliminados,
        'duracion_segundos': duracion_total,
        'ip_origen': ip_saliente,
        'resumen_codigos': resumen_codigos,
        'detalles': detalles,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline de Sincronización y Scraping - Cafésitios")
    parser.add_argument("--workers", type=int, default=None, help="Número de hilos concurrentes (default: 4 o SCRAPER_CONCURRENCY)")
    parser.add_argument("--shard", type=int, default=1, help="Número del shard actual (1-indexed)")
    parser.add_argument("--total-shards", type=int, default=1, help="Total de shards en ejecución paralela")
    parser.add_argument("--tienda-id", type=int, default=None, help="ID específico de una tienda a sincronizar")
    parser.add_argument("--skip-migrations", action="store_true", help="Omitir chequeo de migraciones DDL")

    args, unknown = parser.parse_known_args()

    skip_migrations = (
        args.skip_migrations
        or "--skip-migrations" in sys.argv
        or os.getenv("SKIP_DB_MIGRATIONS", "").strip().lower() in ("true", "1", "yes")
    )

    db = DatabaseManager()
    if not skip_migrations:
        db.inicializar_db()
    else:
        print("⏩ Omitiendo chequeo de migraciones DDL (SKIP_DB_MIGRATIONS activo).")

    tiendas = db.listar_tiendas_activas()

    if args.tienda_id is not None:
        tiendas = [t for t in tiendas if t.get('id') == args.tienda_id]
        print(f"🎯 Modo filtrado: Sincronizando exclusivamente Tienda ID {args.tienda_id} ({len(tiendas)} encontradas).")
    elif args.total_shards > 1:
        # Particionamiento uniforme y determinista
        tiendas = sorted(tiendas, key=lambda t: t['id'])
        total_original = len(tiendas)
        shard_num = max(1, min(args.shard, args.total_shards))
        tiendas = [t for idx, t in enumerate(tiendas) if (idx % args.total_shards) == (shard_num - 1)]
        print(f"🧩 [SHARDING MATRIX] Shard {shard_num}/{args.total_shards} asignado: {len(tiendas)} de {total_original} tiendas totales.")

    workers = args.workers
    res = sincronizar_multiples_tiendas(tiendas, db=db, max_workers=workers, registrar_log_global=True)
    print(f"\nProceso finalizado: {res['tiendas_exitosas']}/{res['total_tiendas']} tiendas sincronizadas correctamente en {res['duracion_segundos']}s.\n")


if __name__ == '__main__':
    main()
