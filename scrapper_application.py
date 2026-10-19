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

from db.database import DatabaseManager
from scrapper.coffee_metadata import (
    extract_coffee_characteristics,
    summarize_extraction_coverage,
    generar_resumen_corto,
)
from core.extractor import CoffeeAttributesExtractor
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver

drivers_por_plataforma = {
    'shopify': ShopifyDriver,
    'woocommerce': WooCommerceDriver,
}


def consumir_productos_tienda(tienda):
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

    errores = []
    for driver_class in driver_classes:
        driver = driver_class(nombre=tienda['nombre'], url_base=tienda['url_base'])
        try:
            return driver.consumir_productos()
        except Exception as error:
            errores.append(f"{driver_class.__name__}: {error}")

    raise RuntimeError(
        f"No se pudo detectar una plataforma válida para '{tienda['nombre']}': "
        + '; '.join(errores)
    )


def sincronizar_tienda(
    tienda: Any,
    db: Any = None,
    extractor: Any = None,
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
            }
        tienda = tienda_dict

    tienda_id = tienda['id']
    nombre_tienda = tienda.get('nombre', f"Tienda #{tienda_id}")

    sincronizacion_id = None
    try:
        sincronizacion_id = db.iniciar_sincronizacion(tienda_id)
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
                    'es_estimado': var.get('es_estimado', True),
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
        })
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
        }
    except Exception as error:
        duracion = round(time.monotonic() - inicio, 2)
        if sincronizacion_id is not None:
            try:
                db.finalizar_sincronizacion(
                    sincronizacion_id,
                    'fallido',
                    detalle_error=str(error),
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
        }


def sincronizar_multiples_tiendas(
    tiendas: list,
    db: Any = None,
    extractor: Any = None,
    registrar_log_global: bool = True,
) -> dict:
    import time
    inicio_corrida = time.monotonic()
    if db is None:
        db = DatabaseManager()
    if extractor is None:
        extractor = CoffeeAttributesExtractor()

    detalles = []
    total_nuevos = 0
    total_actualizados = 0
    total_eliminados = 0
    total_productos_sincronizados = 0
    tiendas_exitosas = 0
    tiendas_fallidas = 0

    for tienda in tiendas:
        res = sincronizar_tienda(tienda, db=db, extractor=extractor)
        detalles.append(res)
        if res['exito']:
            tiendas_exitosas += 1
            total_nuevos += res.get('productos_nuevos', 0)
            total_actualizados += res.get('productos_actualizados', 0)
            total_eliminados += res.get('productos_eliminados', 0)
            total_productos_sincronizados += res.get('total_productos', 0)
            print(f"✅ {res['nombre']}: {res['total_productos']} productos sincronizados ({res['productos_nuevos']} nuevos, {res['productos_actualizados']} actualizados).")
        else:
            tiendas_fallidas += 1
            print(f"❌ {res['nombre']}: {res['error']}")

    duracion_total = round(time.monotonic() - inicio_corrida, 2)
    db.registrar_ultima_sincronizacion()
    if hasattr(db, 'refrescar_vistas_materializadas'):
        try:
            db.refrescar_vistas_materializadas()
        except Exception:
            pass

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
        'detalles': detalles,
    }


def main():
    skip_migrations = (
        "--skip-migrations" in sys.argv
        or os.getenv("SKIP_DB_MIGRATIONS", "").strip().lower() in ("true", "1", "yes")
    )
    db = DatabaseManager()
    if not skip_migrations:
        db.inicializar_db()
    else:
        print("⏩ Omitiendo chequeo de migraciones DDL (SKIP_DB_MIGRATIONS activo).")
    tiendas = db.listar_tiendas_activas()
    res = sincronizar_multiples_tiendas(tiendas, db=db, registrar_log_global=True)
    print(f"\nProceso finalizado: {res['tiendas_exitosas']}/{res['total_tiendas']} tiendas sincronizadas correctamente.\n")


if __name__ == '__main__':
    main()
