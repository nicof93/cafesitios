"""Add tienda_catalogos table and normalize tienda url_base to root domain.

Revision ID: 0017_add_tienda_catalogos
Revises: 0016_add_logo_url_to_tiendas
"""
from urllib.parse import urlparse
from alembic import op
import sqlalchemy as sa

revision = '0017_add_tienda_catalogos'
down_revision = '0016_add_logo_url_to_tiendas'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crear tabla tienda_catalogos
    op.create_table(
        'tienda_catalogos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tienda_id', sa.Integer(), sa.ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url_catalogo', sa.Text(), nullable=False),
        sa.Column('etiqueta', sa.String(length=100), nullable=True),
        sa.Column('activa', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('tienda_id', 'url_catalogo', name='uq_tienda_catalogos_tienda_url'),
    )
    op.create_index('idx_tienda_catalogos_tienda_id', 'tienda_catalogos', ['tienda_id'])

    # 2. Migrar URLs existentes a tienda_catalogos y normalizar url_base al dominio raíz
    bind = op.get_bind()
    tiendas_table = sa.table(
        'tiendas',
        sa.column('id', sa.Integer),
        sa.column('url_base', sa.String),
    )
    catalogos_table = sa.table(
        'tienda_catalogos',
        sa.column('tienda_id', sa.Integer),
        sa.column('url_catalogo', sa.Text),
        sa.column('etiqueta', sa.String),
        sa.column('activa', sa.Boolean),
    )

    rows = bind.execute(sa.select(tiendas_table.c.id, tiendas_table.c.url_base)).fetchall()
    for row in rows:
        store_id, raw_url = row[0], row[1]
        if raw_url and raw_url.strip():
            clean_url = raw_url.strip()
            # Insertar catálogo inicial si no existe
            bind.execute(
                catalogos_table.insert().values(
                    tienda_id=store_id,
                    url_catalogo=clean_url,
                    etiqueta='Catálogo Principal',
                    activa=True,
                )
            )
            # Normalizar url_base a dominio raíz
            try:
                parsed = urlparse(clean_url)
                if parsed.scheme and parsed.netloc:
                    root_domain = f"{parsed.scheme}://{parsed.netloc}"
                    bind.execute(
                        tiendas_table.update()
                        .where(tiendas_table.c.id == store_id)
                        .values(url_base=root_domain)
                    )
            except Exception:
                pass


def downgrade():
    op.drop_index('idx_tienda_catalogos_tienda_id', table_name='tienda_catalogos')
    op.drop_table('tienda_catalogos')

