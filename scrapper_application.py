import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from db.database import DatabaseManager
from scrapper.shopify_driver import ShopifyDriver

tiendas_shopify = [
    {"nombre": "Singular Coffee Roasters", "url_base": "https://singularcoffee.cl/collections/all/products.json"},
    {"nombre": "Café Triciclo", "url_base": "https://www.cafetriciclo.cl/collections/all/products.json"},
    {"nombre": "Coffee Culture Coffee Roasters", "url_base": "https://www.coffeeculture.cl/collections/all/products.json"},
    {"nombre": "Puelo Café", "url_base": "https://puelocafe.cl/collections/all/products.json"},
    {"nombre": "Holaste", "url_base": "https://holaste.cl/collections/cafecito/products.json"},
    {"nombre": "Artisan Roast Chile (Orígenes)", "url_base": "https://shop.artisanroast.cl/collections/origenes/products.json"},
    {"nombre": "Artisan Roast Chile (Blends)", "url_base": "https://shop.artisanroast.cl/collections/blends/products.json"},
    {"nombre": "Dosis - Ultravioleta", "url_base": "https://dosisbebidatiempo.cl/collections/ultravioleta/products.json"}
]

def main():
    db = DatabaseManager()
    db.inicializar_db()

    catalogo_global = []
    print("\n🚀 Iniciando escaneo de tiendas Shopify en Cafe-sitios...\n")

    for tienda in tiendas_shopify:
        driver = ShopifyDriver(nombre=tienda['nombre'], url_base=tienda['url_base'])
        productos = driver.consumir_productos()
        catalogo_global.extend(productos)

    print(f"\n✨ Escaneo completado. Total productos obtenidos: {len(catalogo_global)}")

    print("\n💾 Guardando catálogo e historial de precios en PostgreSQL...")
    db.guardar_catalogo(catalogo_global)
    print("🎉 Proceso finalizado con éxito.\n")

if __name__ == '__main__':
    main()
