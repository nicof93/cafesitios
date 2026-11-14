"""Widen variantes opcion column from 100 to 255 chars.

Revision ID: 0034_widen_variantes_opcion
Revises: 0033_ip_codigos_sync
Create Date: 2026-11-14 09:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0034_widen_variantes_opcion'
down_revision = '0033_ip_codigos_sync'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'variantes' in tables:
        if is_postgres:
            op.alter_column(
                'variantes',
                'opcion',
                existing_type=sa.String(100),
                type_=sa.String(255),
                existing_nullable=False
            )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'variantes' in tables:
        if is_postgres:
            op.alter_column(
                'variantes',
                'opcion',
                existing_type=sa.String(255),
                type_=sa.String(100),
                existing_nullable=False
            )
