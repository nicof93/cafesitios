from typing import List, Literal, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, distinct, func, or_

from domain.repositories import ICoffeeRepository
from domain.models import CoffeeProductDomain, VariantDomain
from db.database import NotaCata, Producto, ProductoNotaCata, Variante, Tienda

class PostgresCoffeeRepository(ICoffeeRepository):
    def __init__(self, session: Session):
        self.session = session

    def _build_base_query(
        self,
        sort_by: Literal["kilo", "unit"] = "kilo",
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
        variety: Optional[str] = None,
        tasting_notes: Optional[str] = None,
    ):
        query = self.session.query(Variante, Producto, Tienda)\
            .join(Producto, Variante.producto_id == Producto.id)\
            .join(Tienda, Producto.tienda_id == Tienda.id)\
            .filter(Producto.activo.is_(True), Tienda.activo.is_(True))

        if only_available:
            query = query.filter(Variante.disponible == True)

        if store_name:
            query = query.filter(Tienda.nombre.ilike(f"%{store_name}%"))

        if process:
            query = query.filter(Producto.proceso.ilike(f"%{process}%"))
        if country:
            query = query.filter(Producto.pais_origen.ilike(f"%{country}%"))
        if variety:
            query = query.filter(Producto.variedad.ilike(f"%{variety}%"))
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

        if tasting_notes:
            note_filter = f"%{tasting_notes}%"
            query = (
                query.join(ProductoNotaCata, ProductoNotaCata.producto_id == Producto.id)
                .join(NotaCata, NotaCata.id == ProductoNotaCata.nota_id)
                .filter(
                    or_(
                        NotaCata.nombre.ilike(note_filter),
                        NotaCata.clave_normalizada.ilike(note_filter),
                    )
                )
            )

        if sort_by == "kilo":
            query = query.order_by(asc(Variante.precio_por_kilo))
        else:
            query = query.order_by(asc(Variante.precio_clp))

        return query

    def count_cheapest_products(
        self,
        sort_by: Literal["kilo", "unit"] = "kilo",
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
        variety: Optional[str] = None,
        tasting_notes: Optional[str] = None,
    ) -> int:
        query = self._build_base_query(
            sort_by=sort_by,
            only_available=only_available,
            store_name=store_name,
            min_weight_g=min_weight_g,
            max_weight_g=max_weight_g,
            search_query=search_query,
            min_price=min_price,
            max_price=max_price,
            process=process,
            country=country,
            variety=variety,
            tasting_notes=tasting_notes,
        )
        return query.with_entities(func.count(distinct(Producto.id))).order_by(None).scalar() or 0

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
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
        variety: Optional[str] = None,
        tasting_notes: Optional[str] = None,
    ) -> List[CoffeeProductDomain]:
        query = self._build_base_query(
            sort_by=sort_by,
            only_available=only_available,
            store_name=store_name,
            min_weight_g=min_weight_g,
            max_weight_g=max_weight_g,
            search_query=search_query,
            min_price=min_price,
            max_price=max_price,
            process=process,
            country=country,
            variety=variety,
            tasting_notes=tasting_notes,
        )

        precio_orden = Variante.precio_por_kilo if sort_by == "kilo" else Variante.precio_clp
        variantes_ordenadas = query.with_entities(
            Variante.id.label("variante_id"),
            func.row_number().over(
                partition_by=Producto.id,
                order_by=(asc(precio_orden), asc(Variante.id)),
            ).label("posicion"),
        ).order_by(None).subquery()

        resultados = (
            query.join(variantes_ordenadas, variantes_ordenadas.c.variante_id == Variante.id)
            .filter(variantes_ordenadas.c.posicion == 1)
            .limit(limit)
            .all()
        )

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
