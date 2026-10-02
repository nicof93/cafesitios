"""Add store platform and per-store synchronization history.

Revision ID: 0002_sync_history
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_sync_history'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tiendas',
        sa.Column('plataforma', sa.String(length=50), server_default='desconocida', nullable=False),
    )
    op.create_table(
        'sincronizaciones',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id'), nullable=False),
        sa.Column('fecha_inicio', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resultado', sa.String(length=20), nullable=False),
        sa.Column('detalle_error', sa.Text(), nullable=True),
        sa.Column('productos_agregados', sa.Integer(), server_default='0', nullable=False),
        sa.Column('productos_eliminados', sa.Integer(), server_default='0', nullable=False),
        sa.Column('productos_actualizados', sa.Integer(), server_default='0', nullable=False),
    )


def downgrade():
    op.drop_table('sincronizaciones')
    op.drop_column('tiendas', 'plataforma')