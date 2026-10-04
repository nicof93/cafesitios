"""Baseline for the existing Cafe-sitios schema.

Revision ID: 0001_baseline
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tiendas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nombre', sa.String(length=100), nullable=False, unique=True),
        sa.Column('url_base', sa.String(length=255), nullable=False),
    )
    op.create_table(
        'productos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id'), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('url_detalle', sa.String(length=500), nullable=False, unique=True),
        sa.Column('imagen', sa.Text(), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'variantes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id'), nullable=False),
        sa.Column('id_variante_externo', sa.String(length=100), nullable=False, unique=True),
        sa.Column('opcion', sa.String(length=100), nullable=False),
        sa.Column('formato_gramos', sa.Integer(), nullable=False),
        sa.Column('precio_clp', sa.Integer(), nullable=False),
        sa.Column('precio_original_clp', sa.Integer(), nullable=False),
        sa.Column('en_oferta', sa.Boolean(), nullable=True),
        sa.Column('descuento_porcentaje', sa.Integer(), nullable=True),
        sa.Column('precio_por_kilo', sa.Numeric(10, 2), nullable=False),
        sa.Column('disponible', sa.Boolean(), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'historial_precios',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('variante_id', sa.Integer(), sa.ForeignKey('variantes.id'), nullable=False),
        sa.Column('precio_clp', sa.Integer(), nullable=False),
        sa.Column('precio_original_clp', sa.Integer(), nullable=False),
        sa.Column('precio_por_kilo', sa.Numeric(10, 2), nullable=False),
        sa.Column('en_oferta', sa.Boolean(), nullable=True),
        sa.Column('descuento_porcentaje', sa.Integer(), nullable=True),
        sa.Column('disponible', sa.Boolean(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'estado_sincronizacion',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ultima_ejecucion', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('estado_sincronizacion')
    op.drop_table('historial_precios')
    op.drop_table('variantes')
    op.drop_table('productos')
    op.drop_table('tiendas')