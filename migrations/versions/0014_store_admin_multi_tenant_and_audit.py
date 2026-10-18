"""Add store admin multi-tenant and audit tables.

Revision ID: 0014_store_admin_multi_tenant
Revises: 0013_weekly_price_drops
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0014_store_admin_multi_tenant'
down_revision = '0013_weekly_price_drops'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    json_type = postgresql.JSONB if is_postgres else sa.JSON

    # 1. Tabla usuarios_tienda
    op.create_table(
        'usuarios_tienda',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('usuario_id', sa.String(36), nullable=False),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rol', sa.String(50), nullable=False, server_default='STORE_ADMIN'),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('usuario_id', 'tienda_id', name='uq_usuario_tienda'),
    )
    op.create_index('idx_usuarios_tienda_usuario_id', 'usuarios_tienda', ['usuario_id'])
    op.create_index('idx_usuarios_tienda_tienda_id', 'usuarios_tienda', ['tienda_id'])

    # 2. Tabla auditoria_acciones_tienda
    op.create_table(
        'auditoria_acciones_tienda',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('usuario_id', sa.String(36), nullable=False),
        sa.Column('accion', sa.String(50), nullable=False),
        sa.Column('entidad', sa.String(50), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=True),
        sa.Column('valores_previos', json_type, nullable=True),
        sa.Column('valores_nuevos', json_type, nullable=True),
        sa.Column('ip_origen', sa.String(45), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_auditoria_tienda_id', 'auditoria_acciones_tienda', ['tienda_id'])
    op.create_index('idx_auditoria_fecha', 'auditoria_acciones_tienda', ['fecha_registro'])
    op.create_index('idx_auditoria_usuario', 'auditoria_acciones_tienda', ['usuario_id'])


def downgrade():
    op.drop_table('auditoria_acciones_tienda')
    op.drop_table('usuarios_tienda')
