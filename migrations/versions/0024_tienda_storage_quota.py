"""Add limite_almacenamiento_mb to tiendas.

Revision ID: 0024_tienda_storage_quota
Revises: 0023_notas_sugeridas
"""
from alembic import op
import sqlalchemy as sa

revision = '0024_tienda_storage_quota'
down_revision = '0023_notas_sugeridas'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'tiendas' in tables:
        cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'limite_almacenamiento_mb' not in cols:
            op.add_column(
                'tiendas',
                sa.Column('limite_almacenamiento_mb', sa.Integer(), nullable=False, server_default='250')
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'tiendas' in tables:
        cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'limite_almacenamiento_mb' in cols:
            op.drop_column('tiendas', 'limite_almacenamiento_mb')

