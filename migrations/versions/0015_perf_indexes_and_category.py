"""Add performance indexes, category column, pg_trgm GIN index, and materialized price variations.

Revision ID: 0015_perf_indexes_and_category
Revises: 0014_store_admin_multi_tenant
"""
from alembic import op
import sqlalchemy as sa

revision = '0015_perf_indexes_and_category'
down_revision = '0014_store_admin_multi_tenant'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Columna categoria en productos
    op.add_column(
        'productos',
        sa.Column('categoria', sa.String(30), nullable=False, server_default='cafe')
    )
    op.create_index('idx_productos_categoria', 'productos', ['categoria'])

    # 2. Índices de llaves foráneas (FKs)
    op.create_index('idx_productos_tienda_id', 'productos', ['tienda_id'])
    op.create_index('idx_variantes_producto_id', 'variantes', ['producto_id'])
    op.create_index('idx_historial_precios_variante_id', 'historial_precios', ['variante_id'])

    # 3. Índices compuestos para catálogo y ordenamiento
    op.create_index('idx_variantes_disponible_kilo', 'variantes', ['disponible', 'precio_por_kilo'])
    op.create_index('idx_variantes_disponible_precio', 'variantes', ['disponible', 'precio_clp'])
    op.create_index('idx_historial_precios_var_fecha', 'historial_precios', ['variante_id', 'fecha_registro'])
    op.create_index('idx_productos_activo_oculto_cat', 'productos', ['activo', 'oculto_catalogo', 'categoria'])

    # 4. Backfill de categoria para productos existentes
    if is_postgres:
        op.execute("""
        UPDATE productos SET categoria = 'no_cafe'
        WHERE LOWER(nombre) ~* '(polera|poleron|hoodie|t-shirt|camiseta|delantal|pechera|apron|calcetin|gorro|jockey|tote|bolso|mochila|iman|reloj|llavero|sticker|taza|tacita|mug|vaso|termo|botella|tumbler|keepcup|cuchara|caja regalo|set regalo|box regalo|gift box|gift card|tarjeta de regalo|suscripcion|subscripcion|membresia|molino|molinillo|grinder|muela|marzocco|appartamento|mozzafiato|cafetera|mokapot|brita|filtro|aeropress|chemex|kettle|tetera|balanza|gramera|bascula|prensa francesa|dripper|portafiltro|tamper|pitcher|jarra|knock box|puck screen|cafiza|rinza|poster|libro|revista|taller|curso|workshop|matcha|chai|sirope|syrup|galleta|alfajor)';
        """)
    else:
        # SQLite: fallback simple para pruebas
        op.execute("""
        UPDATE productos SET categoria = 'no_cafe'
        WHERE LOWER(nombre) LIKE '%taza%'
           OR LOWER(nombre) LIKE '%polera%'
           OR LOWER(nombre) LIKE '%filtro%'
           OR LOWER(nombre) LIKE '%aeropress%'
           OR LOWER(nombre) LIKE '%molino%'
           OR LOWER(nombre) LIKE '%tetera%'
           OR LOWER(nombre) LIKE '%vaso%';
        """)

    # 5. pg_trgm y Materialized View (solo PostgreSQL)
    if is_postgres:
        # Extensión trigramas e índice GIN
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.execute("CREATE INDEX IF NOT EXISTS idx_productos_nombre_trgm ON productos USING gin (nombre gin_trgm_ops);")

        # Materialized View para variaciones de precio
        op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_variaciones_precio AS
        WITH historial_rankeado AS (
            SELECT
                hp.variante_id,
                hp.precio_clp,
                hp.precio_por_kilo,
                hp.fecha_registro,
                ROW_NUMBER() OVER (
                    PARTITION BY hp.variante_id
                    ORDER BY hp.fecha_registro DESC, hp.id DESC
                ) AS rn
            FROM historial_precios hp
        ),
        pares_precio AS (
            SELECT
                v.id AS variante_id,
                p.id AS producto_id,
                p.nombre,
                t.nombre AS tienda,
                v.formato_gramos,
                v.opcion,
                p.url_detalle,
                h_prev.precio_clp AS precio_anterior,
                h_curr.precio_clp AS precio_nuevo,
                h_prev.precio_por_kilo AS precio_kilo_anterior,
                h_curr.precio_por_kilo AS precio_kilo_nuevo,
                h_curr.fecha_registro AS fecha_cambio
            FROM variantes v
            INNER JOIN productos p ON p.id = v.producto_id AND p.activo = TRUE
            INNER JOIN tiendas t ON t.id = p.tienda_id AND t.activo = TRUE
            LEFT JOIN historial_rankeado h_curr ON h_curr.variante_id = v.id AND h_curr.rn = 1
            LEFT JOIN historial_rankeado h_prev ON h_prev.variante_id = v.id AND h_prev.rn = 2
            WHERE h_prev.variante_id IS NOT NULL
        )
        SELECT
            variante_id,
            producto_id,
            nombre,
            tienda,
            formato_gramos,
            opcion,
            url_detalle,
            precio_anterior,
            precio_nuevo,
            (precio_nuevo - precio_anterior) AS diferencia_clp,
            ROUND(
                CASE
                    WHEN precio_anterior > 0 THEN ((precio_nuevo - precio_anterior)::NUMERIC / precio_anterior::NUMERIC) * 100
                    ELSE 0
                END,
                2
            ) AS porcentaje_variacion,
            precio_kilo_anterior,
            precio_kilo_nuevo,
            ROUND((precio_kilo_nuevo - precio_kilo_anterior)::NUMERIC, 2) AS diferencia_kilo_clp,
            CASE
                WHEN precio_nuevo > precio_anterior THEN 'SUBIO'
                WHEN precio_nuevo < precio_anterior THEN 'BAJO'
                ELSE 'SIN_CAMBIO'
            END AS tipo_cambio,
            fecha_cambio
        FROM pares_precio
        WHERE precio_nuevo <> precio_anterior;
        """)

        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_variaciones_variante_id ON mv_variaciones_precio(variante_id);")

        # Actualizar vista_resumen_sincronizacion para consultar mv_variaciones_precio
        op.execute("""
        CREATE OR REPLACE VIEW vista_resumen_sincronizacion AS
        SELECT
            (SELECT fecha_ejecucion FROM sincronizaciones_log WHERE estado = 'OK' ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1) AS ultima_fecha_sincronizacion,
            COALESCE((SELECT estado FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 'OK') AS estado_sincronizacion,
            (SELECT COUNT(*) FROM productos WHERE activo = TRUE) AS total_productos_catalogados,
            COALESCE((SELECT productos_nuevos FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 0) AS productos_nuevos_ultima_pasada,
            (SELECT COUNT(*) FROM variantes WHERE disponible = TRUE) AS disponibilidad_activa,
            (SELECT COUNT(*) FROM mv_variaciones_precio WHERE tipo_cambio = 'SUBIO') AS total_subieron_precio,
            (SELECT COUNT(*) FROM mv_variaciones_precio WHERE tipo_cambio = 'BAJO') AS total_bajaron_precio,
            COALESCE((SELECT ROUND(AVG(porcentaje_variacion), 2) FROM mv_variaciones_precio), 0.0) AS porcentaje_variacion_global;
        """)


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        # Restaurar vista_resumen_sincronizacion a vista estándar
        op.execute("""
        CREATE OR REPLACE VIEW vista_resumen_sincronizacion AS
        SELECT
            (SELECT fecha_ejecucion FROM sincronizaciones_log WHERE estado = 'OK' ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1) AS ultima_fecha_sincronizacion,
            COALESCE((SELECT estado FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 'OK') AS estado_sincronizacion,
            (SELECT COUNT(*) FROM productos WHERE activo = TRUE) AS total_productos_catalogados,
            COALESCE((SELECT productos_nuevos FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 0) AS productos_nuevos_ultima_pasada,
            (SELECT COUNT(*) FROM variantes WHERE disponible = TRUE) AS disponibilidad_activa,
            (SELECT COUNT(*) FROM vista_variaciones_precio WHERE tipo_cambio = 'SUBIO') AS total_subieron_precio,
            (SELECT COUNT(*) FROM vista_variaciones_precio WHERE tipo_cambio = 'BAJO') AS total_bajaron_precio,
            COALESCE((SELECT ROUND(AVG(porcentaje_variacion), 2) FROM vista_variaciones_precio), 0.0) AS porcentaje_variacion_global;
        """)

        op.execute("DROP INDEX IF EXISTS idx_mv_variaciones_variante_id;")
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_variaciones_precio;")
        op.execute("DROP INDEX IF EXISTS idx_productos_nombre_trgm;")

    # Drop composite and FK indexes
    op.drop_index('idx_productos_activo_oculto_cat', table_name='productos')
    op.drop_index('idx_historial_precios_var_fecha', table_name='historial_precios')
    op.drop_index('idx_variantes_disponible_precio', table_name='variantes')
    op.drop_index('idx_variantes_disponible_kilo', table_name='variantes')
    op.drop_index('idx_historial_precios_variante_id', table_name='historial_precios')
    op.drop_index('idx_variantes_producto_id', table_name='variantes')
    op.drop_index('idx_productos_tienda_id', table_name='productos')
    op.drop_index('idx_productos_categoria', table_name='productos')
    op.drop_column('productos', 'categoria')

