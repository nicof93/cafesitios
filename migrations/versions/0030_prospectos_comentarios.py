"""Add prospect columns to tiendas and create tienda_comentarios table.

Revision ID: 0030_prospectos_comentarios
Revises: 0029_confirmar_cafe_moderacion
Create Date: 2026-11-08 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0030_prospectos_comentarios'
down_revision = '0029_confirmar_cafe_moderacion'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    # 1. Agregar columnas a tabla tiendas si existen
    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in insp.get_columns('tiendas')}
        if 'es_prospecto' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('es_prospecto', sa.Boolean(), nullable=False, server_default='false')
            )
        if 'contacto_nombre' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('contacto_nombre', sa.String(150), nullable=True)
            )
        if 'contacto_telefono' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('contacto_telefono', sa.String(50), nullable=True)
            )
        if 'contacto_email' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('contacto_email', sa.String(150), nullable=True)
            )

    # 2. Crear tabla tienda_comentarios
    if 'tienda_comentarios' not in tables:
        op.create_table(
            'tienda_comentarios',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('autor', sa.String(100), nullable=False, server_default='Administrador'),
            sa.Column('tipo_contacto', sa.String(50), nullable=False, server_default='nota'),
            sa.Column('comentario', sa.Text(), nullable=False),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_tienda_comentarios_tienda_id', 'tienda_comentarios', ['tienda_id'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'tienda_comentarios' in tables:
        op.drop_table('tienda_comentarios')

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in insp.get_columns('tiendas')}
        for col_name in ('contacto_email', 'contacto_telefono', 'contacto_nombre', 'es_prospecto'):
            if col_name in tiendas_cols:
                op.drop_column('tiendas', col_name)
