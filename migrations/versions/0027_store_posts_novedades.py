"""Add novedades_tienda table for store announcements and promotions.

Revision ID: 0027_store_posts_novedades
Revises: 0026_store_plans_and_billing
"""
from alembic import op
import sqlalchemy as sa


revision = '0027_store_posts_novedades'
down_revision = '0026_store_plans_and_billing'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'novedades_tienda' not in tables:
        op.create_table(
            'novedades_tienda',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('tienda_id', sa.Integer(), nullable=False),
            sa.Column('titulo', sa.String(length=200), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=False),
            sa.Column('link_url', sa.String(length=500), nullable=True),
            sa.Column('imagen_url', sa.String(length=500), nullable=True),
            sa.Column('categoria_tipo', sa.String(length=50), nullable=True),
            sa.Column('fecha_inicio', sa.DateTime(), nullable=True),
            sa.Column('fecha_fin', sa.DateTime(), nullable=True),
            sa.Column('activo', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('creado_por_rol', sa.String(length=50), server_default='STORE_ADMIN', nullable=False),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tienda_id'], ['tiendas.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_novedades_tienda_fecha', 'novedades_tienda', ['tienda_id', 'fecha_creacion'])
        op.create_index('idx_novedades_activo_fecha', 'novedades_tienda', ['activo', 'fecha_creacion'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'novedades_tienda' in tables:
        op.drop_index('idx_novedades_activo_fecha', table_name='novedades_tienda')
        op.drop_index('idx_novedades_tienda_fecha', table_name='novedades_tienda')
        op.drop_table('novedades_tienda')

