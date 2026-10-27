"""Widen lote column to String(255) in cafes table.

Revision ID: 0025_widen_cafes_lote
Revises: 0024_tienda_storage_quota
"""
from alembic import op
import sqlalchemy as sa

revision = '0025_widen_cafes_lote'
down_revision = '0024_tienda_storage_quota'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'cafes' in tables:
        with op.batch_alter_table('cafes') as batch_op:
            batch_op.alter_column(
                'lote',
                existing_type=sa.String(length=100),
                type_=sa.String(length=255),
                existing_nullable=True,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'cafes' in tables:
        with op.batch_alter_table('cafes') as batch_op:
            batch_op.alter_column(
                'lote',
                existing_type=sa.String(length=255),
                type_=sa.String(length=100),
                existing_nullable=True,
            )

