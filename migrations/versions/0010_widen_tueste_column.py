"""Widen tueste column to String(255) in productos.

Revision ID: 0010_widen_tueste_column
Revises: 0009_cascade_ingestion_tables
"""
from alembic import op
import sqlalchemy as sa

revision = '0010_widen_tueste_column'
down_revision = '0009_cascade_ingestion_tables'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column(
            'tueste',
            existing_type=sa.String(length=50),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column(
            'tueste',
            existing_type=sa.String(length=255),
            type_=sa.String(length=50),
            existing_nullable=True,
        )

