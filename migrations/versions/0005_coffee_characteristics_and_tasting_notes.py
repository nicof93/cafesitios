"""Store extracted coffee characteristics and normalized tasting notes.

Revision ID: 0005_coffee_metadata
Revises: 0004_active_states
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_coffee_metadata'
down_revision = '0004_active_states'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('productos', sa.Column('proceso', sa.String(length=100), nullable=True))
    op.add_column('productos', sa.Column('finca', sa.String(length=255), nullable=True))
    op.add_column('productos', sa.Column('variedad', sa.String(length=255), nullable=True))
    op.add_column('productos', sa.Column('elevacion_min_msnm', sa.Integer(), nullable=True))
    op.add_column('productos', sa.Column('elevacion_max_msnm', sa.Integer(), nullable=True))
    op.add_column('productos', sa.Column('cosecha', sa.String(length=100), nullable=True))
    op.add_column('productos', sa.Column('fermentacion_tipo', sa.String(length=100), nullable=True))
    op.add_column('productos', sa.Column('fermentacion_horas', sa.Numeric(8, 2), nullable=True))
    op.add_column('productos', sa.Column('caracteristicas_fuente', sa.JSON(), nullable=True))

    op.create_table(
        'notas_cata',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('clave_normalizada', sa.String(length=160), nullable=False, unique=True),
        sa.Column('nombre', sa.String(length=160), nullable=False),
    )
    op.create_table(
        'producto_notas_cata',
        sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id'), primary_key=True),
        sa.Column('nota_id', sa.Integer(), sa.ForeignKey('notas_cata.id'), primary_key=True),
        sa.Column('texto_origen', sa.Text(), nullable=False),
        sa.Column('confianza', sa.Float(), nullable=False),
        sa.Column('version_extractor', sa.String(length=50), nullable=False),
    )


def downgrade():
    op.drop_table('producto_notas_cata')
    op.drop_table('notas_cata')
    op.drop_column('productos', 'caracteristicas_fuente')
    op.drop_column('productos', 'fermentacion_horas')
    op.drop_column('productos', 'fermentacion_tipo')
    op.drop_column('productos', 'cosecha')
    op.drop_column('productos', 'elevacion_max_msnm')
    op.drop_column('productos', 'elevacion_min_msnm')
    op.drop_column('productos', 'variedad')
    op.drop_column('productos', 'finca')
    op.drop_column('productos', 'proceso')