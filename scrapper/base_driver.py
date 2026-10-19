import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.normalizer import CoffeeDataNormalizer

logger = logging.getLogger(__name__)


def limpiar_precio_clp(texto: Any) -> int:
    """Extrae un valor numérico entero en CLP a partir de cualquier texto o número.
    Ej: '$ 12.990' -> 12990, '9.500 CLP' -> 9500, 8500.0 -> 8500
    """
    if texto is None:
        return 0
    if isinstance(texto, (int, float)):
        return int(texto)
    raw = str(texto).strip()
    # Si viene con decimales estilo '12.990,00' o '12990.00'
    if ',' in raw and '.' in raw:
        # Asume formato chileno: punto para miles, coma para centavos
        raw = raw.split(',')[0]
    elif '.' in raw and len(raw.split('.')[-1]) <= 2:
        # Formato anglosajón '12990.00'
        raw = raw.split('.')[0]

    # Quitar cualquier carácter no numérico
    digits = re.sub(r'[^\d]', '', raw)
    return int(digits) if digits else 0


class DriverExtractorPort(ABC):
    """Puerto / Interfaz canónica para todos los drivers de extracción (Arquitectura Hexagonal)."""

    @abstractmethod
    def consumir_productos(self) -> List[Dict[str, Any]]:
        """Retorna productos con su jerarquía completa (producto -> variantes)

        para la orquestación y base de datos.
        """
        pass

    @abstractmethod
    def extraer_ofertas(self) -> List[Dict[str, Any]]:
        """Retorna una lista plana normalizada de ofertas:

        {
            "nombre_producto": str,
            "precio_actual": int,
            "formato_gramos": int,
            "precio_por_kilo": float,
            "link_detalle": str,
            "imagen_url": str,
            "disponible": bool,
            "plataforma": str
        }
        """
        pass


class BaseDriver(DriverExtractorPort):
    """Clase base para drivers de extracción web/API."""

    def __init__(self, nombre: str, url_base: str, plataforma: str = "desconocida"):
        self.nombre = nombre
        self.url_base = url_base
        self.plataforma = plataforma

    @staticmethod
    def extraer_gramos(texto: Optional[str], default: int = 250) -> int:
        return CoffeeDataNormalizer.extraer_gramos(texto, default=default)

    @staticmethod
    def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
        return CoffeeDataNormalizer.calcular_precio_por_kilo(precio_clp, formato_gramos)

    @staticmethod
    def limpiar_precio(texto: Any) -> int:
        return limpiar_precio_clp(texto)

    def extraer_ofertas(self) -> List[Dict[str, Any]]:
        """Convierte los productos y variantes extraídos en una lista plana de ofertas normalizadas."""
        productos = self.consumir_productos()
        ofertas: List[Dict[str, Any]] = []
        for prod in productos:
            nombre = prod.get("nombre", "")
            img = prod.get("imagen") or ""
            link_base = prod.get("url_detalle") or self.url_base
            variantes = prod.get("variantes") or []

            if not variantes:
                # Si no tiene variantes declaradas, generar una oferta con los datos base
                ofertas.append(
                    CoffeeDataNormalizer.normalizar_oferta(
                        nombre_producto=nombre,
                        precio_actual=0,
                        formato_gramos=250,
                        link_detalle=link_base,
                        imagen_url=img,
                        disponible=True,
                        plataforma=self.plataforma,
                    )
                )
            else:
                for var in variantes:
                    var_link = link_base
                    var_id = var.get("id_variante_externo")
                    if var_id and "?" not in var_link:
                        var_link = f"{var_link}?variant={var_id}"

                    ofertas.append(
                        CoffeeDataNormalizer.normalizar_oferta(
                            nombre_producto=nombre,
                            precio_actual=var.get("precio_clp", 0),
                            formato_gramos=var.get("formato_gramos", 250),
                            link_detalle=var_link,
                            imagen_url=img,
                            disponible=var.get("disponible", True),
                            plataforma=self.plataforma,
                        )
                    )
        return ofertas

