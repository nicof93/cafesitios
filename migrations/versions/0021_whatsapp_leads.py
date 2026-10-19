"""Add whatsapp_leads table and store telefono_whatsapp.

Revision ID: 0021_whatsapp_leads
Revises: 0020_add_partial_index_visibles
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0021_whatsapp_leads'
down_revision = '0020_add_partial_index_visibles'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgres = bind.dialect.name == 'postgresql'
    json_type = postgresql.JSONB if is_postgres else sa.JSON

    tables = inspector.get_table_names()

    # 1. Agregar columna telefono_whatsapp a tiendas si no existe
    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'telefono_whatsapp' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('telefono_whatsapp', sa.String(50), nullable=True)
            )

    # 2. Crear tabla pedidos_whatsapp si no existe
    if 'pedidos_whatsapp' not in tables:
        op.create_table(
            'pedidos_whatsapp',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('dispositivo_uuid', sa.String(100), nullable=False),
            sa.Column('monto_total_clp', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('items', json_type, nullable=False),
            sa.Column('estado', sa.String(50), nullable=False, server_default='ENVIADO'),
            sa.Column('ip_origen', sa.String(50), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('idx_pedidos_whatsapp_tienda_id', 'pedidos_whatsapp', ['tienda_id'])
        op.create_index('idx_pedidos_whatsapp_tienda_fecha', 'pedidos_whatsapp', ['tienda_id', 'fecha_creacion'])
        op.create_index('idx_pedidos_whatsapp_dispositivo', 'pedidos_whatsapp', ['dispositivo_uuid'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'pedidos_whatsapp' in tables:
        op.drop_table('pedidos_whatsapp')

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'telefono_whatsapp' in tiendas_cols:
            op.drop_column('tiendas', 'telefono_whatsapp')
