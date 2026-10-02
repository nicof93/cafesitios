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

tiendas_shopify = [
    {"nombre": "Singular Coffee Roasters", "url_base": "https://singularcoffee.cl/collections/all/products.json"},
    {"nombre": "Café Triciclo", "url_base": "https://www.cafetriciclo.cl/collections/all/products.json"},
    {"nombre": "Coffee Culture Coffee Roasters", "url_base": "https://www.coffeeculture.cl/collections/all/products.json"},
    {"nombre": "Puelo Café", "url_base": "https://puelocafe.cl/collections/all/products.json"},
    {"nombre": "Holaste", "url_base": "https://holaste.cl/collections/cafecito/products.json"},
    {"nombre": "Artisan Roast Chile (Orígenes)", "url_base": "https://shop.artisanroast.cl/collections/origenes/products.json"},
    {"nombre": "Artisan Roast Chile (Blends)", "url_base": "https://shop.artisanroast.cl/collections/blends/products.json"},
    {"nombre": "Dosis - Ultravioleta", "url_base": "https://dosisbebidatiempo.cl/collections/ultravioleta/products.json"},
    {"nombre": "WR4 / WRoasters", "url_base": "https://www.wearefour.cl/collections/tuestes/products.json"}
]

tiendas_woocommerce = [
    {"nombre": "Café Altura", "url_base": "https://cafealtura.cl/wp-json/wc/store/v1/products?category=cafe-en-grano"}
]

def main():
    db = DatabaseManager()
    db.inicializar_db()

    resultados = []
    configuraciones = [
        ('shopify', tiendas_shopify, ShopifyDriver),
        ('woocommerce', tiendas_woocommerce, WooCommerceDriver),
    ]

    for plataforma, tiendas, driver_class in configuraciones:
        for tienda in tiendas:
            sincronizacion_id = db.iniciar_sincronizacion(
                tienda['nombre'], tienda['url_base'], plataforma
            )
            try:
                driver = driver_class(nombre=tienda['nombre'], url_base=tienda['url_base'])
                productos = driver.consumir_productos()
                conteos = db.guardar_catalogo(
                    productos,
                    nombre_tienda=tienda['nombre'],
                    url_base=tienda['url_base'],
                    plataforma=plataforma,
                )
                db.finalizar_sincronizacion(sincronizacion_id, 'exitoso', **{
                    'productos_agregados': conteos['agregados'],
                    'productos_eliminados': conteos['eliminados'],
                    'productos_actualizados': conteos['actualizados'],
                })
                resultados.append(True)
                print(f"✅ {tienda['nombre']}: {len(productos)} productos sincronizados.")
            except Exception as error:
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
