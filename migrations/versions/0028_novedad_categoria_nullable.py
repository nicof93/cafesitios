"""Make categoria_tipo nullable in novedades_tienda.

Revision ID: 0028_novedad_categoria_nullable
Revises: 0027_store_posts_novedades
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0028_novedad_categoria_nullable'
down_revision = '0027_store_posts_novedades'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.alter_column('novedades_tienda', 'categoria_tipo', nullable=True)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.alter_column('novedades_tienda', 'categoria_tipo', nullable=False)

