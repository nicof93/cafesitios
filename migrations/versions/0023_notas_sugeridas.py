"""Add estado and es_fuera_de_rueda to producto_notas_cata.

Revision ID: 0023_notas_sugeridas
Revises: 0022_shipping_and_roast
"""
from alembic import op
import sqlalchemy as sa

revision = '0023_notas_sugeridas'
down_revision = '0022_shipping_and_roast'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'producto_notas_cata' in tables:
        cols = {col['name'] for col in inspector.get_columns('producto_notas_cata')}
        if 'estado' not in cols:
            op.add_column(
                'producto_notas_cata',
                sa.Column('estado', sa.String(20), nullable=False, server_default='confirmada')
            )
        if 'es_fuera_de_rueda' not in cols:
            op.add_column(
                'producto_notas_cata',
                sa.Column('es_fuera_de_rueda', sa.Boolean(), nullable=False, server_default=sa.text('false'))
            )

        # Crear índice compuesto si no existe
        indexes = {idx['name'] for idx in inspector.get_indexes('producto_notas_cata')}
        if 'idx_producto_notas_estado' not in indexes:
            op.create_index(
                'idx_producto_notas_estado',
                'producto_notas_cata',
                ['producto_id', 'estado']
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'producto_notas_cata' in tables:
        indexes = {idx['name'] for idx in inspector.get_indexes('producto_notas_cata')}
        if 'idx_producto_notas_estado' in indexes:
            op.drop_index('idx_producto_notas_estado', table_name='producto_notas_cata')

        cols = {col['name'] for col in inspector.get_columns('producto_notas_cata')}
        if 'es_fuera_de_rueda' in cols:
            op.drop_column('producto_notas_cata', 'es_fuera_de_rueda')
        if 'estado' in cols:
            op.drop_column('producto_notas_cata', 'estado')

