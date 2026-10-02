"""Add logical product deletion and store activation state.

Revision ID: 0004_active_states
Revises: 0003_product_identity
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_active_states'
down_revision = '0003_product_identity'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tiendas',
        sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        'productos',
        sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade():
    op.drop_column('productos', 'activo')
    op.drop_column('tiendas', 'activo')