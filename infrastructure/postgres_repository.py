from typing import List, Literal, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, distinct, func, not_, or_

from domain.repositories import ICoffeeRepository
from domain.models import CoffeeProductDomain, VariantDomain
from domain.search_normalizer import (
    NON_COFFEE_KEYWORDS_SQL,
    classify_product_category,
    expand_search_terms,
    get_synonym_group,
)
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
        min_price_kilo: Optional[int] = None,
        max_price_kilo: Optional[int] = None,
        category: Optional[str] = "cafe",
    ):
        query = self.session.query(Variante, Producto, Tienda)\
            .join(Producto, Variante.producto_id == Producto.id)\
            .join(Tienda, Producto.tienda_id == Tienda.id)\
            .filter(
                Producto.activo.is_(True),
                Producto.oculto_catalogo.is_(False),
                Tienda.activo.is_(True),
            )

        if category == "cafe":
            query = query.filter(Producto.categoria == "cafe")
        elif category in ("no_cafe", "otros", "merch"):
            query = query.filter(Producto.categoria != "cafe")

        if only_available:
            query = query.filter(Variante.disponible == True)


        if store_name:
            if isinstance(store_name, str):
                stores = [s.strip() for s in store_name.split(",") if s.strip()]
            elif isinstance(store_name, (list, tuple, set)):
                stores = [str(s).strip() for s in store_name if str(s).strip()]
            else:
                stores = [str(store_name).strip()]

            if len(stores) == 1:
                query = query.filter(Tienda.nombre.ilike(f"%{stores[0]}%"))
            elif len(stores) > 1:
                query = query.filter(or_(*[Tienda.nombre.ilike(f"%{s}%") for s in stores]))

        if process:
            proc_synonyms = get_synonym_group(process)
            query = query.filter(or_(*[Producto.proceso.ilike(f"%{p}%") for p in proc_synonyms]))

        if country:
            query = query.filter(Producto.pais_origen.ilike(f"%{country}%"))

        if variety:
            var_synonyms = get_synonym_group(variety)
            query = query.filter(or_(*[Producto.variedad.ilike(f"%{v}%") for v in var_synonyms]))

        if min_weight_g is not None:
            query = query.filter(Variante.formato_gramos >= min_weight_g)
        if max_weight_g is not None:
            query = query.filter(Variante.formato_gramos <= max_weight_g)

        if search_query:
            expanded = expand_search_terms(search_query)
            clauses = [Producto.nombre.ilike(f"%{term}%") for term in expanded]
            query = query.filter(or_(*clauses))

        if min_price is not None:
            query = query.filter(Variante.precio_clp >= min_price)
        if max_price is not None:
            query = query.filter(Variante.precio_clp <= max_price)

        if min_price_kilo is not None:
            query = query.filter(Variante.precio_por_kilo >= min_price_kilo)
        if max_price_kilo is not None:
            query = query.filter(Variante.precio_por_kilo <= max_price_kilo)

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
        min_price_kilo: Optional[int] = None,
        max_price_kilo: Optional[int] = None,
        category: Optional[str] = "cafe",
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
            min_price_kilo=min_price_kilo,
            max_price_kilo=max_price_kilo,
            category=category,
        )
        return query.with_entities(func.count(distinct(Producto.id))).order_by(None).scalar() or 0

    def get_cheapest_products(
        self,
        sort_by: Literal["kilo", "unit"] = "kilo",
        limit: int = 10,
        offset: int = 0,
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
        min_price_kilo: Optional[int] = None,
        max_price_kilo: Optional[int] = None,
        category: Optional[str] = "cafe",
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
            min_price_kilo=min_price_kilo,
            max_price_kilo=max_price_kilo,
            category=category,
        )

        precio_orden = Variante.precio_por_kilo if sort_by == "kilo" else Variante.precio_clp
        variantes_ordenadas = query.with_entities(
            Variante.id.label("variante_id"),
            func.row_number().over(
                partition_by=Producto.id,
                order_by=(asc(precio_orden), asc(Variante.id)),
            ).label("posicion"),
        ).order_by(None).subquery()

        consulta_final = (
            query.join(variantes_ordenadas, variantes_ordenadas.c.variante_id == Variante.id)
            .filter(variantes_ordenadas.c.posicion == 1)
        )
        if offset > 0:
            consulta_final = consulta_final.offset(offset)
        resultados = consulta_final.limit(limit).all()

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
                disponible=var.disponible,
                es_estimado=bool(getattr(var, 'es_estimado', True))
            )

            prod_dom = CoffeeProductDomain(
                id=prod.id,
                tienda=tienda.nombre,
                nombre=prod.nombre,
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                descripcion=prod.descripcion,
                variante_mas_barata=variante_dom,
                categoria=classify_product_category(prod.nombre),
                oculto_catalogo=bool(getattr(prod, 'oculto_catalogo', False)),
            )
            productos_dominio.append(prod_dom)

        return productos_dominio

    def find_matching_products(self, product_id: int) -> List[CoffeeProductDomain]:
        """Busca productos idénticos en otras tiendas bajo la regla de Identidad Estricta de Grano (RN-04)."""
        target = (
            self.session.query(Producto)
            .filter(
                Producto.id == product_id,
                Producto.activo.is_(True),
                Producto.oculto_catalogo.is_(False),
            )
            .first()
        )
        if not target or not target.pais_origen:
            return []

        # Para identidad estricta se requiere coincidencia en pais_origen y al menos variedad o proceso
        query = (
            self.session.query(Variante, Producto, Tienda)
            .join(Producto, Variante.producto_id == Producto.id)
            .join(Tienda, Producto.tienda_id == Tienda.id)
            .filter(
                Producto.id != target.id,
                Producto.tienda_id != target.tienda_id,
                Producto.activo.is_(True),
                Producto.oculto_catalogo.is_(False),
                Tienda.activo.is_(True),
                Variante.disponible == True,
                Producto.pais_origen.ilike(target.pais_origen),
            )
        )

        if target.finca:
            query = query.filter(Producto.finca.ilike(f"%{target.finca}%"))
        if target.variedad:
            var_syn = get_synonym_group(target.variedad)
            query = query.filter(or_(*[Producto.variedad.ilike(f"%{v}%") for v in var_syn]))
        if target.proceso:
            proc_syn = get_synonym_group(target.proceso)
            query = query.filter(or_(*[Producto.proceso.ilike(f"%{p}%") for p in proc_syn]))

        query = query.order_by(asc(Variante.precio_por_kilo))

        variantes_ordenadas = query.with_entities(
            Variante.id.label("variante_id"),
            func.row_number().over(
                partition_by=Producto.id,
                order_by=(asc(Variante.precio_por_kilo), asc(Variante.id)),
            ).label("posicion"),
        ).order_by(None).subquery()

        resultados = (
            query.join(variantes_ordenadas, variantes_ordenadas.c.variante_id == Variante.id)
            .filter(variantes_ordenadas.c.posicion == 1)
            .limit(5)
            .all()
        )

        matches = []
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
                disponible=var.disponible,
                es_estimado=bool(getattr(var, 'es_estimado', True))
            )
            matches.append(
                CoffeeProductDomain(
                    id=prod.id,
                    tienda=tienda.nombre,
                    nombre=prod.nombre,
                    url_detalle=prod.url_detalle,
                    imagen=prod.imagen,
                    descripcion=prod.descripcion,
                    variante_mas_barata=variante_dom,
                    categoria=classify_product_category(prod.nombre),
                    oculto_catalogo=bool(getattr(prod, 'oculto_catalogo', False)),
                )
            )
        return matches
