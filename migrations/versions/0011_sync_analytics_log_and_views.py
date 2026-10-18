"""Create sincronizaciones_log table and sync analytics views.

Revision ID: 0011_sync_analytics_views
Revises: 0010_widen_tueste_column
"""
from alembic import op
import sqlalchemy as sa

revision = '0011_sync_analytics_views'
down_revision = '0010_widen_tueste_column'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'sincronizaciones_log' not in existing_tables:
        op.create_table(
            'sincronizaciones_log',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('fecha_ejecucion', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('estado', sa.String(length=20), nullable=False, server_default='OK'),
            sa.Column('productos_nuevos', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('productos_actualizados', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('productos_con_cambio_precio', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('duracion_segundos', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('mensaje_error', sa.Text(), nullable=True),
        )

    existing_indexes = {
        idx['name'] for idx in inspector.get_indexes('sincronizaciones_log')
    } if 'sincronizaciones_log' in set(sa.inspect(bind).get_table_names()) else set()

    if 'idx_sincronizaciones_log_fecha_ejecucion' not in existing_indexes:
        op.create_index(
            'idx_sincronizaciones_log_fecha_ejecucion',
            'sincronizaciones_log',
            ['fecha_ejecucion'],
        )
    if 'idx_sincronizaciones_log_estado' not in existing_indexes:
        op.create_index(
            'idx_sincronizaciones_log_estado',
            'sincronizaciones_log',
            ['estado'],
        )

    if is_postgres:
        op.execute("""
        CREATE OR REPLACE VIEW vista_variaciones_precio AS
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
                p.nombre AS nombre,
                t.nombre AS tienda,
                v.formato_gramos,
                v.opcion,
                p.url_detalle,
                COALESCE(h_prev.precio_clp, h_curr.precio_clp, v.precio_original_clp) AS precio_anterior,
                COALESCE(h_curr.precio_clp, v.precio_clp) AS precio_nuevo,
                COALESCE(h_prev.precio_por_kilo, h_curr.precio_por_kilo, v.precio_por_kilo) AS precio_kilo_anterior,
                COALESCE(h_curr.precio_por_kilo, v.precio_por_kilo) AS precio_kilo_nuevo,
                COALESCE(h_curr.fecha_registro, v.fecha_actualizacion) AS fecha_cambio
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
    else:
        op.execute("""
        CREATE VIEW IF NOT EXISTS vista_resumen_sincronizacion AS
        SELECT
            (SELECT fecha_ejecucion FROM sincronizaciones_log WHERE estado = 'OK' ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1) AS ultima_fecha_sincronizacion,
            COALESCE((SELECT estado FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 'SIN_DATOS') AS estado_sincronizacion,
            (SELECT COUNT(*) FROM productos WHERE activo = 1) AS total_productos_catalogados,
            COALESCE((SELECT productos_nuevos FROM sincronizaciones_log ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1), 0) AS productos_nuevos_ultima_pasada,
            (SELECT COUNT(*) FROM variantes WHERE disponible = 1) AS disponibilidad_activa,
            0 AS total_subieron_precio,
            0 AS total_bajaron_precio,
            0.0 AS porcentaje_variacion_global;
        """)


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    if is_postgres:
        op.execute("DROP VIEW IF EXISTS vista_resumen_sincronizacion;")
        op.execute("DROP VIEW IF EXISTS vista_variaciones_precio;")
    else:
        op.execute("DROP VIEW IF EXISTS vista_resumen_sincronizacion;")
    op.drop_index('idx_sincronizaciones_log_estado', table_name='sincronizaciones_log')
    op.drop_index('idx_sincronizaciones_log_fecha_ejecucion', table_name='sincronizaciones_log')
    op.drop_table('sincronizaciones_log')
