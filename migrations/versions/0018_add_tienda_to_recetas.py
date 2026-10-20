"""Add tienda_id, autor_tipo and es_publica to recetas.

Revision ID: 0018_add_tienda_to_recetas
Revises: 0017_add_tienda_catalogos
"""
from alembic import op
import sqlalchemy as sa

revision = '0018_add_tienda_to_recetas'
down_revision = '0017_add_tienda_catalogos'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    inspector = sa.inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('recetas')}

    if 'tienda_id' not in existing_columns:
        if is_postgres:
            op.add_column(
                'recetas',
                sa.Column(
                    'tienda_id',
                    sa.Integer(),
                    sa.ForeignKey('tiendas.id', ondelete='CASCADE'),
                    nullable=True,
                )
            )
        else:
            op.add_column(
                'recetas',
                sa.Column('tienda_id', sa.Integer(), nullable=True)
            )
        try:
            op.create_index('idx_recetas_tienda_id', 'recetas', ['tienda_id'])
        except Exception:
            pass

    if 'autor_tipo' not in existing_columns:
        op.add_column(
            'recetas',
            sa.Column('autor_tipo', sa.String(50), server_default='barista', nullable=False)
        )

    if 'es_publica' not in existing_columns:
        op.add_column(
            'recetas',
            sa.Column('es_publica', sa.Boolean(), server_default='true', nullable=False)
        )

    if 'catacion_sca' not in existing_columns:
        op.add_column(
            'recetas',
            sa.Column('catacion_sca', sa.JSON(), nullable=True)
        )

    if 'puntuacion_sca_total' not in existing_columns:
        op.add_column(
            'recetas',
            sa.Column('puntuacion_sca_total', sa.Numeric(5, 2), nullable=True)
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('recetas')}

    if 'tienda_id' in existing_columns:
        try:
            op.drop_index('idx_recetas_tienda_id', table_name='recetas')
        except Exception:
            pass
        op.drop_column('recetas', 'tienda_id')

    if 'autor_tipo' in existing_columns:
        op.drop_column('recetas', 'autor_tipo')

    if 'es_publica' in existing_columns:
        op.drop_column('recetas', 'es_publica')
