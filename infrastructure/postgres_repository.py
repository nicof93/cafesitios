from typing import List, Literal, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc

from domain.repositories import ICoffeeRepository
from domain.models import CoffeeProductDomain, VariantDomain
from db.database import Producto, Variante, Tienda

class PostgresCoffeeRepository(ICoffeeRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_cheapest_products(
        self, 
        sort_by: Literal["kilo", "unit"] = "kilo", 
        limit: int = 10, 
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[CoffeeProductDomain]:
        
        query = self.session.query(Variante, Producto, Tienda)\
            .join(Producto, Variante.producto_id == Producto.id)\
            .join(Tienda, Producto.tienda_id == Tienda.id)

        if only_available:
            query = query.filter(Variante.disponible == True)

        if store_name:
            query = query.filter(Tienda.nombre.ilike(f"%{store_name}%"))

        if min_weight_g is not None:
            query = query.filter(Variante.formato_gramos >= min_weight_g)
        if max_weight_g is not None:
            query = query.filter(Variante.formato_gramos <= max_weight_g)

        if search_query:
            query = query.filter(Producto.nombre.ilike(f"%{search_query}%"))

        if min_price is not None:
            query = query.filter(Variante.precio_clp >= min_price)
        if max_price is not None:
            query = query.filter(Variante.precio_clp <= max_price)

        if sort_by == "kilo":
            query = query.order_by(asc(Variante.precio_por_kilo))
        else:
            query = query.order_by(asc(Variante.precio_clp))

        resultados = query.limit(limit).all()

        productos_dominio = []
        for var, prod, tienda in resultados:
            variante_dom = VariantDomain(
                id_externo=var.id_variante_externo,
                opcion=var.opcion,
                formato_gramos=var.formato_gramos,
                precio_clp=var.precio_clp,
                precio_original_clp=var.precio_original_clp,
                en_oferta=var.en_oferta,
                descuento_porcentaje=var.descuento_porcentaje,
                precio_por_kilo=float(var.precio_por_kilo),
                disponible=var.disponible
            )

            prod_dom = CoffeeProductDomain(
                id=prod.id,
                tienda=tienda.nombre,
                nombre=prod.nombre,
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                descripcion=prod.descripcion,
                variante_mas_barata=variante_dom
            )
            productos_dominio.append(prod_dom)

        return productos_dominio
