"""Add partial index for non-hidden active products in public catalog.

Revision ID: 0020_add_partial_index_visibles
Revises: 0019_pass_and_recipe_steps
"""
from alembic import op
import sqlalchemy as sa

revision = '0020_add_partial_index_visibles'
down_revision = '0019_pass_and_recipe_steps'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        op.execute("""
        CREATE INDEX IF NOT EXISTS idx_productos_visibles_catalogo 
        ON productos (categoria, tienda_id, id) 
        WHERE activo = TRUE AND oculto_catalogo = FALSE;
        """)
    else:
        # SQLite: soporte nativo de indices parciales con WHERE
        op.execute("""
        CREATE INDEX IF NOT EXISTS idx_productos_visibles_catalogo 
        ON productos (categoria, tienda_id, id) 
        WHERE activo = 1 AND oculto_catalogo = 0;
        """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_productos_visibles_catalogo;")

