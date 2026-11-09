"""Add profile, services and menu to tiendas.

Revision ID: 0031_perfil_servicios_menu
Revises: 0030_prospectos_comentarios
Create Date: 2026-11-09 09:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from core.slug_helper import slugify


revision = '0031_perfil_servicios_menu'
down_revision = '0030_prospectos_comentarios'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in insp.get_columns('tiendas')}

        if 'slug' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('slug', sa.String(100), nullable=True)
            )

        if 'descripcion' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('descripcion', sa.Text(), nullable=True)
            )

        if 'servicios' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('servicios', sa.JSON(), nullable=True)
            )

        if 'carta_comida_url' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('carta_comida_url', sa.String(500), nullable=True)
            )

        if 'carta_comida_tamano_bytes' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('carta_comida_tamano_bytes', sa.Integer(), nullable=True, server_default='0')
            )

        if 'instagram_url' not in tiendas_cols:
            op.add_column(
                'tiendas',
                sa.Column('instagram_url', sa.String(255), nullable=True)
            )

        # Crear índice único para slug si no existe
        existing_indices = {idx['name'] for idx in insp.get_indexes('tiendas')}
        if 'idx_tiendas_slug' not in existing_indices:
            try:
                op.create_index('idx_tiendas_slug', 'tiendas', ['slug'], unique=True)
            except Exception:
                pass

        # Poblar slugs iniciales para tiendas que no tengan slug
        connection = bind
        rows = connection.execute(sa.text("SELECT id, nombre, slug FROM tiendas")).fetchall()
        used_slugs = set()
        for row in rows:
            t_id, t_nombre, current_slug = row[0], row[1], row[2]
            if current_slug:
                used_slugs.add(current_slug)
            else:
                base_slug = slugify(t_nombre) or f"tienda-{t_id}"
                candidate = base_slug
                counter = 2
                while candidate in used_slugs:
                    candidate = f"{base_slug}-{counter}"
                    counter += 1
                used_slugs.add(candidate)
                connection.execute(
                    sa.text("UPDATE tiendas SET slug = :slug WHERE id = :id"),
                    {"slug": candidate, "id": t_id}
                )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'tiendas' in tables:
        tiendas_cols = {col['name'] for col in insp.get_columns('tiendas')}
        existing_indices = {idx['name'] for idx in insp.get_indexes('tiendas')}

        if 'idx_tiendas_slug' in existing_indices:
            try:
                op.drop_index('idx_tiendas_slug', table_name='tiendas')
            except Exception:
                pass

        for col in [
            'instagram_url', 'carta_comida_tamano_bytes', 'carta_comida_url',
            'servicios', 'descripcion', 'slug'
        ]:
            if col in tiendas_cols:
                try:
                    op.drop_column('tiendas', col)
                except Exception:
                    pass
