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

from db.database import DatabaseManager
from scrapper.coffee_metadata import (
    extract_coffee_characteristics,
    summarize_extraction_coverage,
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
        driver_classes = [drivers_por_plataforma[plataforma]]
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


def main():
    db = DatabaseManager()
    db.inicializar_db()
    tiendas = db.listar_tiendas_activas()

    resultados = []
    for tienda in tiendas:
        sincronizacion_id = None
        try:
            sincronizacion_id = db.iniciar_sincronizacion(tienda['id'])
            productos = consumir_productos_tienda(tienda)
            extractor = CoffeeAttributesExtractor()
            catalogo_cascada = []

            for producto in productos:
                producto['caracteristicas_cafe'] = extract_coffee_characteristics(
                    producto.get('descripcion')
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

            coverage = summarize_extraction_coverage([
                producto['caracteristicas_cafe'] for producto in productos
            ])
            conteos = db.guardar_catalogo(productos, tienda_id=tienda['id'])
            db.guardar_cafes_cascada(catalogo_cascada, tienda_id=tienda['id'])

            db.finalizar_sincronizacion(sincronizacion_id, 'exitoso', **{
                'productos_agregados': conteos['agregados'],
                'productos_eliminados': conteos['eliminados'],
                'productos_actualizados': conteos['actualizados'],
            })
            resultados.append(True)
            print(f"✅ {tienda['nombre']}: {len(productos)} productos sincronizados.")
            field_coverage = ', '.join(
                f"{field} {stats['detectados']}/{coverage['total']}"
                for field, stats in coverage['campos'].items()
            )
            print(
                f"   Cobertura de extracción: {coverage['con_datos']}/{coverage['total']} "
                f"productos ({coverage['porcentaje_con_datos']}%); {field_coverage}"
            )
        except Exception as error:
            if sincronizacion_id is not None:
                db.finalizar_sincronizacion(
                    sincronizacion_id,
                    'fallido',
                    detalle_error=str(error),
                )
            resultados.append(False)
            print(f"❌ {tienda['nombre']}: {error}")

    db.registrar_ultima_sincronizacion()
    total_exitosas = sum(resultados)
    print(f"\nProceso finalizado: {total_exitosas}/{len(resultados)} tiendas sincronizadas correctamente.\n")


if __name__ == '__main__':
    main()
