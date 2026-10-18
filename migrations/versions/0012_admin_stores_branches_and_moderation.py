"""Add sucursales_tienda table, tienda.direccion, producto.oculto_catalogo and clean invalid tasting notes.

Revision ID: 0012_admin_stores_moderation
Revises: 0011_sync_analytics_views
"""
from alembic import op
import sqlalchemy as sa

revision = '0012_admin_stores_moderation'
down_revision = '0011_sync_analytics_views'
branch_labels = None
depends_on = None

INVALID_NOTE_KEYS = (
    'historia', 'nuestra-historia', 'la-historia', 'origen', 'pais', 'region',
    'finca', 'productor', 'productores', 'cooperativa', 'beneficio', 'proceso',
    'variedad', 'varietal', 'cultivar', 'altitud', 'altura', 'elevacion', 'msnm',
    'cosecha', 'lote', 'tueste', 'nivel-de-tueste', 'agtron', 'puntaje',
    'puntuacion', 'sca', 'puntos', 'descripcion', 'informacion', 'ficha',
    'ficha-tecnica', 'caracteristicas', 'detalle', 'detalles', 'notas',
    'notas-de-cata', 'perfil', 'perfil-de-taza', 'sensorial', 'cata',
    'preparacion', 'metodo', 'receta', 'recomendacion', 'molienda', 'grano',
    'grano-entero', 'molido', 'formato', 'peso', 'bolsa', 'envase', 'pack',
    'stock', 'disponible', 'envio', 'despacho', 'tienda', 'comprar', 'precio',
    'oferta', 'cafe', 'cafe-de-especialidad', 'arabica', 'robusta', 'blend',
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'tiendas' in existing_tables:
        tienda_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'direccion' not in tienda_cols:
            op.add_column('tiendas', sa.Column('direccion', sa.String(length=255), nullable=True))

    if 'productos' in existing_tables:
        prod_cols = {col['name'] for col in inspector.get_columns('productos')}
        if 'oculto_catalogo' not in prod_cols:
            op.add_column(
                'productos',
                sa.Column('oculto_catalogo', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            )

    if 'sucursales_tienda' not in existing_tables:
        op.create_table(
            'sucursales_tienda',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('nombre', sa.String(length=150), nullable=False),
            sa.Column('direccion', sa.String(length=255), nullable=True),
            sa.Column('comuna', sa.String(length=100), nullable=True),
            sa.Column('region', sa.String(length=100), nullable=True),
            sa.Column('latitud', sa.Numeric(10, 8), nullable=True),
            sa.Column('longitud', sa.Numeric(11, 8), nullable=True),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    refreshed_tables = set(sa.inspect(bind).get_table_names())
    if 'sucursales_tienda' in refreshed_tables:
        existing_idx = {idx['name'] for idx in sa.inspect(bind).get_indexes('sucursales_tienda')}
        if 'ix_sucursales_tienda_tienda_id' not in existing_idx:
            op.create_index('ix_sucursales_tienda_tienda_id', 'sucursales_tienda', ['tienda_id'])

    if 'notas_cata' in refreshed_tables and 'producto_notas_cata' in refreshed_tables:
        placeholders = ', '.join(f"'{k}'" for k in INVALID_NOTE_KEYS)
        op.execute(
            sa.text(
                f"DELETE FROM producto_notas_cata WHERE nota_id IN "
                f"(SELECT id FROM notas_cata WHERE LOWER(clave_normalizada) IN ({placeholders}) "
                f"OR LOWER(nombre) IN ({placeholders}))"
            )
        )
        op.execute(
            sa.text(
                f"DELETE FROM notas_cata WHERE LOWER(clave_normalizada) IN ({placeholders}) "
                f"OR LOWER(nombre) IN ({placeholders})"
            )
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'sucursales_tienda' in existing_tables:
        existing_idx = {idx['name'] for idx in inspector.get_indexes('sucursales_tienda')}
        if 'ix_sucursales_tienda_tienda_id' in existing_idx:
            op.drop_index('ix_sucursales_tienda_tienda_id', table_name='sucursales_tienda')
        op.drop_table('sucursales_tienda')

    if 'productos' in existing_tables:
        prod_cols = {col['name'] for col in inspector.get_columns('productos')}
        if 'oculto_catalogo' in prod_cols:
            op.drop_column('productos', 'oculto_catalogo')

    if 'tiendas' in existing_tables:
        tienda_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'direccion' in tienda_cols:
            op.drop_column('tiendas', 'direccion')
