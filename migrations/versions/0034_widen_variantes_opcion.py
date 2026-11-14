"""Widen variantes opcion column from 100 to 255 chars with materialized view handling.

Revision ID: 0034_widen_variantes_opcion
Revises: 0033_ip_codigos_sync
Create Date: 2026-11-14 09:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0034_widen_variantes_opcion'
down_revision = '0033_ip_codigos_sync'
branch_labels = None
depends_on = None


_MV_VARIACIONES_SQL = """
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
"""

_VISTA_RESUMEN_SQL = """
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
"""


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if is_postgres and 'variantes' in tables:
        # En PostgreSQL: La vista materializada mv_variaciones_precio y vista_resumen_sincronizacion
        # dependen de la columna opcion. Se deben eliminar antes de alterar el tipo y recrearse despues.
        op.execute("DROP VIEW IF EXISTS vista_resumen_sincronizacion CASCADE;")
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_variaciones_precio CASCADE;")

        op.alter_column(
            'variantes',
            'opcion',
            existing_type=sa.String(100),
            type_=sa.String(255),
            existing_nullable=False
        )

        op.execute(_MV_VARIACIONES_SQL)
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_variaciones_variante_id ON mv_variaciones_precio(variante_id);")
        op.execute(_VISTA_RESUMEN_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if is_postgres and 'variantes' in tables:
        op.execute("DROP VIEW IF EXISTS vista_resumen_sincronizacion CASCADE;")
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_variaciones_precio CASCADE;")

        op.alter_column(
            'variantes',
            'opcion',
            existing_type=sa.String(255),
            type_=sa.String(100),
            existing_nullable=False
        )

        op.execute(_MV_VARIACIONES_SQL)
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_variaciones_variante_id ON mv_variaciones_precio(variante_id);")
        op.execute(_VISTA_RESUMEN_SQL)
