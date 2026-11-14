"""Add ip_origen and http codes to sincronizaciones and sincronizaciones_log.

Revision ID: 0033_ip_codigos_sync
Revises: 0032_catas_y_panel_sensorial
Create Date: 2026-11-14 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0033_ip_codigos_sync'
down_revision = '0032_catas_y_panel_sensorial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    # 1. Agregar ip_origen y resumen_codigos a sincronizaciones_log
    if 'sincronizaciones_log' in tables:
        log_cols = {col['name'] for col in insp.get_columns('sincronizaciones_log')}
        if 'ip_origen' not in log_cols:
            op.add_column(
                'sincronizaciones_log',
                sa.Column('ip_origen', sa.String(50), nullable=True)
            )
        if 'resumen_codigos' not in log_cols:
            op.add_column(
                'sincronizaciones_log',
                sa.Column('resumen_codigos', sa.JSON(), nullable=True)
            )

    # 2. Agregar ip_origen y codigo_http a sincronizaciones
    if 'sincronizaciones' in tables:
        sync_cols = {col['name'] for col in insp.get_columns('sincronizaciones')}
        if 'ip_origen' not in sync_cols:
            op.add_column(
                'sincronizaciones',
                sa.Column('ip_origen', sa.String(50), nullable=True)
            )
        if 'codigo_http' not in sync_cols:
            op.add_column(
                'sincronizaciones',
                sa.Column('codigo_http', sa.Integer(), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'sincronizaciones' in tables:
        sync_cols = {col['name'] for col in insp.get_columns('sincronizaciones')}
        if 'codigo_http' in sync_cols:
            op.drop_column('sincronizaciones', 'codigo_http')
        if 'ip_origen' in sync_cols:
            op.drop_column('sincronizaciones', 'ip_origen')

    if 'sincronizaciones_log' in tables:
        log_cols = {col['name'] for col in insp.get_columns('sincronizaciones_log')}
        if 'resumen_codigos' in log_cols:
            op.drop_column('sincronizaciones_log', 'resumen_codigos')
        if 'ip_origen' in log_cols:
            op.drop_column('sincronizaciones_log', 'ip_origen')
