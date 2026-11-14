"""Add catas and cata_respuestas tables for sensory cupping panels.

Revision ID: 0032_catas_y_panel_sensorial
Revises: 0031_perfil_servicios_menu
Create Date: 2026-11-12 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0032_catas_y_panel_sensorial'
down_revision = '0031_perfil_servicios_menu'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'catas' not in tables:
        op.create_table(
            'catas',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id', ondelete='SET NULL'), nullable=True),
            sa.Column('nombre', sa.String(120), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('token_publico', sa.String(64), nullable=False),
            sa.Column('fecha_expiracion', sa.DateTime(), nullable=False),
            sa.Column('estado', sa.String(20), nullable=False, server_default='activa'),
            sa.Column('valores_iniciales_75', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('publicar_en_producto', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('idx_catas_tienda_id', 'catas', ['tienda_id'])
        op.create_index('idx_catas_producto_id', 'catas', ['producto_id'])
        op.create_index('idx_catas_token_publico', 'catas', ['token_publico'], unique=True)
        op.create_index('idx_catas_tienda_estado', 'catas', ['tienda_id', 'estado'])

    if 'cata_respuestas' not in tables:
        op.create_table(
            'cata_respuestas',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('cata_id', sa.Integer(), sa.ForeignKey('catas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('nombre_catador', sa.String(100), nullable=False),
            sa.Column('fragancia_aroma', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('sabor', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('sabor_residual', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('acidez', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('cuerpo', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('uniformidad', sa.Float(), nullable=False, server_default='10.0'),
            sa.Column('balance', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('taza_limpia', sa.Float(), nullable=False, server_default='10.0'),
            sa.Column('dulzor', sa.Float(), nullable=False, server_default='10.0'),
            sa.Column('puntaje_general', sa.Float(), nullable=False, server_default='7.5'),
            sa.Column('defectos', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('puntaje_total', sa.Float(), nullable=False),
            sa.Column('notas_identificadas', sa.JSON(), nullable=True),
            sa.Column('observaciones', sa.Text(), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('idx_cata_respuestas_cata_id', 'cata_respuestas', ['cata_id'])
        op.create_index('idx_cata_respuestas_cata_fecha', 'cata_respuestas', ['cata_id', 'fecha_creacion'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'cata_respuestas' in tables:
        op.drop_table('cata_respuestas')

    if 'catas' in tables:
        op.drop_table('catas')
