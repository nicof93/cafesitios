from typing import Dict, List, Optional, Type
from scrapper.base_driver import BaseDriver
from scrapper.jumpseller_driver import JumpsellerDriver
from scrapper.odoo_driver import OdooDriver
from scrapper.prestashop_driver import PrestaShopDriver
from scrapper.shopify_driver import ShopifyDriver
from scrapper.sumup_driver import SumUpDriver
from scrapper.woocommerce_driver import WooCommerceDriver


class DriverFactory:
    """Factoría para instanciar el driver de extracción correspondiente según la plataforma."""

    _drivers: Dict[str, Type[BaseDriver]] = {
        'shopify': ShopifyDriver,
        'woocommerce': WooCommerceDriver,
        'jumpseller': JumpsellerDriver,
        'prestashop': PrestaShopDriver,
        'odoo': OdooDriver,
        'sumup': SumUpDriver,
    }

    @classmethod
    def registrar_driver(cls, plataforma: str, driver_cls: Type[BaseDriver]) -> None:
        cls._drivers[plataforma.lower()] = driver_cls

    @classmethod
    def obtener_clase_driver(cls, plataforma: Optional[str]) -> Optional[Type[BaseDriver]]:
        if not plataforma:
            return None
        return cls._drivers.get(plataforma.strip().lower())

    @classmethod
    def obtener_driver(
        cls, plataforma: Optional[str], nombre: str, url_base: str
    ) -> Optional[BaseDriver]:
        driver_cls = cls.obtener_clase_driver(plataforma)
        if driver_cls:
            return driver_cls(nombre=nombre, url_base=url_base)
        return None

    @classmethod
    def plataformas_soportadas(cls) -> List[str]:
        return list(cls._drivers.keys())

