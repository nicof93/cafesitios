import logging
from typing import Optional
from urllib.parse import quote_plus
from sqlalchemy import distinct, func, not_, or_, select
from sqlalchemy.orm import Session

from db.database import NovedadTienda, Producto, Tienda, Variante
from domain.search_normalizer import NON_COFFEE_KEYWORDS_SQL

logger = logging.getLogger(__name__)


def contar_cafes_activos_tienda(tienda_id: int, db_session: Session) -> int:
    """Calcula la cantidad exacta de cafés activos, disponibles y visibles en catálogo para una tienda."""
    non_coffee_clauses = [Producto.nombre.ilike(f"%{kw}%") for kw in NON_COFFEE_KEYWORDS_SQL]

    stmt = (
        select(func.count(distinct(Producto.id)))
        .join(Variante, Variante.producto_id == Producto.id)
        .where(
            Producto.tienda_id == tienda_id,
            Producto.activo.is_(True),
            Producto.oculto_catalogo.is_(False),
            Variante.disponible.is_(True),
            not_(or_(*non_coffee_clauses)),
        )
    )
    return db_session.execute(stmt).scalar() or 0


def sincronizar_novedad_nueva_tienda(tienda_id: int, db_session: Session) -> Optional[NovedadTienda]:
    """
    Crea o actualiza de manera reactiva la publicación de bienvenida en Novedades
    (categoria_tipo='nueva_tienda') para una tostaduría incorporada a Cafésitios.
    """
    tienda = db_session.execute(
        select(Tienda).where(Tienda.id == tienda_id)
    ).scalar_one_or_none()

    if not tienda:
        logger.warning(f"No se encontró la tienda con ID {tienda_id} para sincronizar novedad.")
        return None

    cant_cafes = contar_cafes_activos_tienda(tienda_id, db_session)
    clean_nombre = tienda.nombre.strip()
    catalog_link = f"/catalogo?tienda={quote_plus(clean_nombre)}"

    if cant_cafes > 0:
        plural = "café disponible" if cant_cafes == 1 else "cafés disponibles"
        desc = (
            f"¡Damos una calurosa bienvenida a {clean_nombre} a Cafésitios! "
            f"Actualmente contamos con {cant_cafes} {plural} en nuestro catálogo para comparar precios y notas de cata."
        )
    else:
        desc = (
            f"¡Damos una calurosa bienvenida a {clean_nombre} a Cafésitios! "
            f"Estamos preparando su catálogo para que muy pronto puedas comparar todos sus orígenes y procesos."
        )

    # Buscar si ya existe una novedad de tipo 'nueva_tienda' para esta tostaduría
    novedad = db_session.execute(
        select(NovedadTienda).where(
            NovedadTienda.tienda_id == tienda_id,
            NovedadTienda.categoria_tipo == "nueva_tienda",
        )
    ).scalar_one_or_none()

    if novedad is None:
        novedad = NovedadTienda(
            tienda_id=tienda.id,
            titulo=f"¡Bienvenida {clean_nombre} a Cafésitios! 🎉",
            descripcion=desc,
            link_url=catalog_link,
            imagen_url=tienda.logo_url,
            categoria_tipo="nueva_tienda",
            creado_por_rol="PLATFORM_ADMIN",
            activo=bool(tienda.activo),
        )
        db_session.add(novedad)
        logger.info(f"Creada novedad de bienvenida para tienda {clean_nombre} (ID: {tienda_id}).")
    else:
        novedad.descripcion = desc
        novedad.link_url = catalog_link
        if tienda.logo_url and not novedad.imagen_url:
            novedad.imagen_url = tienda.logo_url
        novedad.activo = bool(tienda.activo)
        logger.info(f"Actualizada novedad de bienvenida para tienda {clean_nombre} ({cant_cafes} cafés).")

    return novedad
