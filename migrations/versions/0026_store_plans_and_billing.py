"""Add planes_tienda, pagos_tienda and store billing columns.

Revision ID: 0026_store_plans_and_billing
Revises: 0025_widen_cafes_lote
"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


revision = '0026_store_plans_and_billing'
down_revision = '0025_widen_cafes_lote'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Crear tabla planes_tienda
    if 'planes_tienda' not in tables:
        op.create_table(
            'planes_tienda',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('nombre', sa.String(length=100), nullable=False),
            sa.Column('codigo', sa.String(length=50), nullable=False),
            sa.Column('precio_mensual_clp', sa.Integer(), server_default='0', nullable=False),
            sa.Column('descripcion', sa.String(length=255), nullable=True),
            sa.Column('limite_almacenamiento_mb', sa.Integer(), server_default='250', nullable=False),
            sa.Column('funcionalidades', sa.JSON(), nullable=False),
            sa.Column('activo', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_planes_tienda_codigo', 'planes_tienda', ['codigo'], unique=True)

        # Seed inicial de los 3 planes predeterminados
        planes_table = sa.table(
            'planes_tienda',
            sa.column('nombre', sa.String),
            sa.column('codigo', sa.String),
            sa.column('precio_mensual_clp', sa.Integer),
            sa.column('descripcion', sa.String),
            sa.column('limite_almacenamiento_mb', sa.Integer),
            sa.column('funcionalidades', sa.JSON),
            sa.column('activo', sa.Boolean),
            sa.column('fecha_creacion', sa.DateTime),
            sa.column('fecha_actualizacion', sa.DateTime)
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        op.bulk_insert(
            planes_table,
            [
                {
                    'nombre': 'Plan Básico',
                    'codigo': 'plan_basico',
                    'precio_mensual_clp': 0,
                    'descripcion': 'Visibilidad en catálogo público, clics salientes y métricas esenciales.',
                    'limite_almacenamiento_mb': 250,
                    'funcionalidades': {
                        'whatsapp_orders': False,
                        'recetas_oficiales': False,
                        'radar_demanda': False,
                        'benchmark_precios': False,
                        'fotos_hd_extra': False,
                        'destacado_catalogo': False,
                    },
                    'activo': True,
                    'fecha_creacion': now,
                    'fecha_actualizacion': now,
                },
                {
                    'nombre': 'Plan Pro Tostaduría',
                    'codigo': 'plan_pro',
                    'precio_mensual_clp': 19990,
                    'descripcion': 'Ventas WhatsApp 0% comisión, Recetas Oficiales y almacenamiento ampliado a 500 MB.',
                    'limite_almacenamiento_mb': 500,
                    'funcionalidades': {
                        'whatsapp_orders': True,
                        'recetas_oficiales': True,
                        'radar_demanda': False,
                        'benchmark_precios': False,
                        'fotos_hd_extra': True,
                        'destacado_catalogo': False,
                    },
                    'activo': True,
                    'fecha_creacion': now,
                    'fecha_actualizacion': now,
                },
                {
                    'nombre': 'Plan Premium Partner',
                    'codigo': 'plan_premium',
                    'precio_mensual_clp': 39990,
                    'descripcion': 'Suite completa: Ventas WhatsApp, Radar de Demanda, Benchmark y 2 GB de almacenamiento.',
                    'limite_almacenamiento_mb': 2000,
                    'funcionalidades': {
                        'whatsapp_orders': True,
                        'recetas_oficiales': True,
                        'radar_demanda': True,
                        'benchmark_precios': True,
                        'fotos_hd_extra': True,
                        'destacado_catalogo': True,
                    },
                    'activo': True,
                    'fecha_creacion': now,
                    'fecha_actualizacion': now,
                },
            ]
        )

    # 2. Agregar columnas en tiendas
    if 'tiendas' in tables:
        cols = {col['name'] for col in inspector.get_columns('tiendas')}
        if 'plan_id' not in cols:
            if is_postgres:
                op.add_column('tiendas', sa.Column('plan_id', sa.Integer(), sa.ForeignKey('planes_tienda.id', ondelete='SET NULL'), nullable=True))
            else:
                op.add_column('tiendas', sa.Column('plan_id', sa.Integer(), nullable=True))
            try:
                op.create_index('idx_tiendas_plan_id', 'tiendas', ['plan_id'])
            except Exception:
                pass
        if 'dia_pago_mensual' not in cols:
            op.add_column('tiendas', sa.Column('dia_pago_mensual', sa.Integer(), server_default='5', nullable=False))
        if 'precio_acordado_clp' not in cols:
            op.add_column('tiendas', sa.Column('precio_acordado_clp', sa.Integer(), nullable=True))
        if 'estado_pago' not in cols:
            op.add_column('tiendas', sa.Column('estado_pago', sa.String(length=50), server_default='AL_DIA', nullable=False))
        if 'funcionalidades_override' not in cols:
            op.add_column('tiendas', sa.Column('funcionalidades_override', sa.JSON(), nullable=True))

    # 3. Crear tabla pagos_tienda
    if 'pagos_tienda' not in tables:
        op.create_table(
            'pagos_tienda',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
            sa.Column('monto_clp', sa.Integer(), nullable=False),
            sa.Column('fecha_pago', sa.DateTime(), nullable=False),
            sa.Column('periodo_mes', sa.Integer(), nullable=False),
            sa.Column('periodo_anio', sa.Integer(), nullable=False),
            sa.Column('estado', sa.String(length=50), server_default='PAGADO', nullable=False),
            sa.Column('metodo_pago', sa.String(length=50), server_default='TRANSFERENCIA', nullable=False),
            sa.Column('referencia_comprobante', sa.String(length=150), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_pagos_tienda_fecha', 'pagos_tienda', ['tienda_id', 'fecha_pago'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'pagos_tienda' in tables:
        op.drop_table('pagos_tienda')

    if 'tiendas' in tables:
        cols = {col['name'] for col in inspector.get_columns('tiendas')}
        for col_name in ['funcionalidades_override', 'estado_pago', 'precio_acordado_clp', 'dia_pago_mensual', 'plan_id']:
            if col_name in cols:
                op.drop_column('tiendas', col_name)

    if 'planes_tienda' in tables:
        op.drop_table('planes_tienda')
