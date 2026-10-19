"""Add password and change flag to usuarios_tienda, and borrador/pasos to recetas.

Revision ID: 0019_pass_and_recipe_steps
Revises: 0018_add_tienda_to_recetas
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import postgresql

revision = '0019_pass_and_recipe_steps'
down_revision = '0018_add_tienda_to_recetas'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    is_postgres = bind.dialect.name == 'postgresql'
    json_type = postgresql.JSONB if is_postgres else sa.JSON

    # 1. Columnas en usuarios_tienda
    tables = inspector.get_table_names()
    if 'usuarios_tienda' in tables:
        usuarios_tienda_cols = {col['name'] for col in inspector.get_columns('usuarios_tienda')}
        if 'password_hash' not in usuarios_tienda_cols:
            op.add_column(
                'usuarios_tienda',
                sa.Column('password_hash', sa.String(255), nullable=True)
            )
        if 'debe_cambiar_password' not in usuarios_tienda_cols:
            op.add_column(
                'usuarios_tienda',
                sa.Column('debe_cambiar_password', sa.Boolean(), server_default='true', nullable=False)
            )

    # 2. Columnas en recetas
    if 'recetas' in tables:
        recetas_cols = {col['name'] for col in inspector.get_columns('recetas')}
        if 'es_borrador' not in recetas_cols:
            op.add_column(
                'recetas',
                sa.Column('es_borrador', sa.Boolean(), server_default='false', nullable=False)
            )
        if 'pasos' not in recetas_cols:
            op.add_column(
                'recetas',
                sa.Column('pasos', json_type, nullable=True)
            )


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'usuarios_tienda' in tables:
        usuarios_tienda_cols = {col['name'] for col in inspector.get_columns('usuarios_tienda')}
        if 'debe_cambiar_password' in usuarios_tienda_cols:
            op.drop_column('usuarios_tienda', 'debe_cambiar_password')
        if 'password_hash' in usuarios_tienda_cols:
            op.drop_column('usuarios_tienda', 'password_hash')

    if 'recetas' in tables:
        recetas_cols = {col['name'] for col in inspector.get_columns('recetas')}
        if 'pasos' in recetas_cols:
            op.drop_column('recetas', 'pasos')
        if 'es_borrador' in recetas_cols:
            op.drop_column('recetas', 'es_borrador')

