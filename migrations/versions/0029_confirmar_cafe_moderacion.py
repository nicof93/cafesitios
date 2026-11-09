"""Add es_cafe_confirmado to productos table.

Revision ID: 0029_confirmar_cafe_moderacion
Revises: 0028_novedad_categoria_nullable
Create Date: 2026-11-08
"""
from alembic import op
import sqlalchemy as sa


revision = '0029_confirmar_cafe_moderacion'
down_revision = '0028_novedad_categoria_nullable'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'productos' in tables:
        cols = {col['name'] for col in inspector.get_columns('productos')}
        if 'es_cafe_confirmado' not in cols:
            op.add_column(
                'productos',
                sa.Column('es_cafe_confirmado', sa.Boolean(), nullable=False, server_default='false')
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'productos' in tables:
        cols = {col['name'] for col in inspector.get_columns('productos')}
        if 'es_cafe_confirmado' in cols:
            op.drop_column('productos', 'es_cafe_confirmado')
