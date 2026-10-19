"""Add logo_url to tiendas table.

Revision ID: 0016_add_logo_url_to_tiendas
Revises: 0015_perf_indexes_and_category
"""
from alembic import op
import sqlalchemy as sa

revision = '0016_add_logo_url_to_tiendas'
down_revision = '0015_perf_indexes_and_category'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tiendas',
        sa.Column('logo_url', sa.String(500), nullable=True)
    )


def downgrade():
    op.drop_column('tiendas', 'logo_url')

