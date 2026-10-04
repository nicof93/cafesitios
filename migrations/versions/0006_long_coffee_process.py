"""Allow full process and fermentation descriptions.

Revision ID: 0006_long_coffee_process
Revises: 0005_coffee_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_long_coffee_process'
down_revision = '0005_coffee_metadata'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column(
            'proceso',
            existing_type=sa.String(length=100),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'fermentacion_tipo',
            existing_type=sa.String(length=100),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column(
            'proceso',
            existing_type=sa.Text(),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'fermentacion_tipo',
            existing_type=sa.Text(),
            type_=sa.String(length=100),
            existing_nullable=True,
        )