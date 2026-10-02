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
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver

drivers_por_plataforma = {
    'shopify': ShopifyDriver,
    'woocommerce': WooCommerceDriver,
}


def main():
    db = DatabaseManager()
    db.inicializar_db()
    tiendas = db.listar_tiendas_activas()

    resultados = []
    for tienda in tiendas:
        sincronizacion_id = None
        try:
            sincronizacion_id = db.iniciar_sincronizacion(tienda['id'])
            driver_class = drivers_por_plataforma.get(tienda['plataforma'].lower())
            if driver_class is None:
                raise ValueError(f"Plataforma no soportada: {tienda['plataforma']}")

            driver = driver_class(nombre=tienda['nombre'], url_base=tienda['url_base'])
            productos = driver.consumir_productos()
            conteos = db.guardar_catalogo(productos, tienda_id=tienda['id'])
            db.finalizar_sincronizacion(sincronizacion_id, 'exitoso', **{
                'productos_agregados': conteos['agregados'],
                'productos_eliminados': conteos['eliminados'],
                'productos_actualizados': conteos['actualizados'],
            })
            resultados.append(True)
            print(f"✅ {tienda['nombre']}: {len(productos)} productos sincronizados.")
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
