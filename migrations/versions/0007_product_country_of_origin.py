"""Add country of origin to coffee products.

Revision ID: 0007_product_country
Revises: 0006_long_coffee_process
"""
from alembic import op
import sqlalchemy as sa

revision = '0007_product_country'
down_revision = '0006_long_coffee_process'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('productos', sa.Column('pais_origen', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('productos', 'pais_origen')