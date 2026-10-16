"""Add MVP core features: store geolocation, estimated price flag, recipes, feedback, clicks, search history.

Revision ID: 0008_mvp_core_features
Revises: 0007_product_country
"""
from alembic import op
import sqlalchemy as sa

revision = '0008_mvp_core_features'
down_revision = '0007_product_country'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Columnas en tiendas
    op.add_column('tiendas', sa.Column('latitud', sa.Numeric(10, 8), nullable=True))
    op.add_column('tiendas', sa.Column('longitud', sa.Numeric(11, 8), nullable=True))
    op.add_column('tiendas', sa.Column('comuna', sa.String(length=100), nullable=True))

    # 2. Columna en variantes y productos
    op.add_column('variantes', sa.Column('es_estimado', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('productos', sa.Column('tueste', sa.String(length=50), nullable=True))

    # 3. Tabla recetas
    op.create_table(
        'recetas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dispositivo_uuid', sa.String(length=64), nullable=False, index=True),
        sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('nombre_receta', sa.String(length=150), nullable=False),
        sa.Column('metodo', sa.String(length=100), nullable=False),
        sa.Column('dosis_cafe_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('agua_ml', sa.Numeric(6, 2), nullable=False),
        sa.Column('ratio', sa.String(length=20), nullable=True),
        sa.Column('molino_usado', sa.String(length=100), nullable=True),
        sa.Column('grosor_molienda', sa.String(length=50), nullable=True),
        sa.Column('temperatura_c', sa.Integer(), nullable=True),
        sa.Column('tiempo_total_s', sa.Integer(), nullable=True),
        sa.Column('calificacion_1_10', sa.Integer(), nullable=True),
        sa.Column('reintentar', sa.Boolean(), server_default=sa.true(), nullable=True),
        sa.Column('notas_catado', sa.Text(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 4. Tabla sugerencias_feedback
    op.create_table(
        'sugerencias_feedback',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('contacto_opcional', sa.String(length=150), nullable=True),
        sa.Column('ip_hash', sa.String(length=64), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 5. Tabla interacciones_clics
    op.create_table(
        'interacciones_clics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('producto_id', sa.Integer(), sa.ForeignKey('productos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('variante_id', sa.Integer(), sa.ForeignKey('variantes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tipo_evento', sa.String(length=50), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=False),
        sa.Column('metadata_evento', sa.JSON(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 6. Tabla historial_busquedas
    op.create_table(
        'historial_busquedas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('termino_busqueda', sa.String(length=255), nullable=False),
        sa.Column('resultados_encontrados', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('historial_busquedas')
    op.drop_table('interacciones_clics')
    op.drop_table('sugerencias_feedback')
    op.drop_table('recetas')
    op.drop_column('variantes', 'es_estimado')
    op.drop_column('productos', 'tueste')
    op.drop_column('tiendas', 'comuna')
    op.drop_column('tiendas', 'longitud')
    op.drop_column('tiendas', 'latitud')
