"""Add cascade ingestion tables (cafes, ofertas_tienda) and pg_trgm extension.

Revision ID: 0009_cascade_ingestion_tables
Revises: 0008_mvp_core_features
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0009_cascade_ingestion_tables'
down_revision = '0008_mvp_core_features'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Habilitar extensión pg_trgm en PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Crear tabla cafes
    array_type = postgresql.ARRAY(sa.Text()) if is_postgres else sa.JSON()

    op.create_table(
        'cafes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('origen', sa.String(length=255), nullable=True),
        sa.Column('finca_productor', sa.String(length=255), nullable=True),
        sa.Column('variedad', sa.String(length=255), nullable=True),
        sa.Column('proceso', sa.String(length=255), nullable=True),
        sa.Column('lote', sa.String(length=100), nullable=True),
        sa.Column('notas_cata', array_type, nullable=True),
        sa.Column('notas_normalizadas', array_type, nullable=True),
        sa.Column('hash_descripcion', sa.String(length=32), nullable=True, index=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 3. Índices GIN con trigramas para búsqueda difusa en PostgreSQL
    if is_postgres:
        op.execute("CREATE INDEX IF NOT EXISTS idx_cafes_nombre_trgm ON cafes USING gin (nombre gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_cafes_origen_trgm ON cafes USING gin (origen gin_trgm_ops);")

    # 4. Crear tabla ofertas_tienda
    op.create_table(
        'ofertas_tienda',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cafe_id', sa.Integer(), sa.ForeignKey('cafes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('precio_actual', sa.Integer(), nullable=False),
        sa.Column('formato_gramos', sa.Integer(), nullable=False),
        sa.Column('precio_por_kilo', sa.Numeric(10, 2), nullable=False),
        sa.Column('es_estimado', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('link_detalle', sa.String(length=500), unique=True, nullable=False),
        sa.Column('disponible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('ultima_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    op.drop_table('ofertas_tienda')
    if is_postgres:
        op.execute("DROP INDEX IF EXISTS idx_cafes_origen_trgm;")
        op.execute("DROP INDEX IF EXISTS idx_cafes_nombre_trgm;")
    op.drop_table('cafes')

