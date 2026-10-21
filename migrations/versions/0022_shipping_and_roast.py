"""Add shipping and roast fields to tiendas.

Revision ID: 0022_shipping_and_roast
Revises: 0021_whatsapp_leads
"""
from alembic import op
import sqlalchemy as sa

revision = '0022_shipping_and_roast'
down_revision = '0021_whatsapp_leads'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'envio_gratis_monto' not in tiendas_cols:
            op.add_column('tiendas', sa.Column('envio_gratis_monto', sa.Integer(), nullable=True))
        if 'retiro_en_tienda' not in tiendas_cols:
            op.add_column('tiendas', sa.Column('retiro_en_tienda', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        if 'dias_tueste' not in tiendas_cols:
            op.add_column('tiendas', sa.Column('dias_tueste', sa.String(100), nullable=True))
        if 'fecha_ultimo_tueste' not in tiendas_cols:
            op.add_column('tiendas', sa.Column('fecha_ultimo_tueste', sa.Date(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'fecha_ultimo_tueste' in tiendas_cols:
            op.drop_column('tiendas', 'fecha_ultimo_tueste')
        if 'dias_tueste' in tiendas_cols:
            op.drop_column('tiendas', 'dias_tueste')
        if 'retiro_en_tienda' in tiendas_cols:
            op.drop_column('tiendas', 'retiro_en_tienda')
        if 'envio_gratis_monto' in tiendas_cols:
            op.drop_column('tiendas', 'envio_gratis_monto')

