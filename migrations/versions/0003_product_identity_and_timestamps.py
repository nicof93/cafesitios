"""Add creation timestamps and external product identity.

Revision ID: 0003_product_identity
Revises: 0002_sync_history
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_product_identity'
down_revision = '0002_sync_history'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tiendas', sa.Column('fecha_creacion', sa.DateTime(), nullable=True))
    op.add_column('tiendas', sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True))
    op.add_column('productos', sa.Column('id_externo', sa.String(length=255), nullable=True))
    op.add_column('productos', sa.Column('fecha_creacion', sa.DateTime(), nullable=True))
    op.add_column('variantes', sa.Column('fecha_creacion', sa.DateTime(), nullable=True))

    op.execute(sa.text(
        "UPDATE tiendas SET fecha_creacion = CURRENT_TIMESTAMP, "
        "fecha_actualizacion = CURRENT_TIMESTAMP"
    ))
    op.execute(sa.text(
        "UPDATE productos SET fecha_creacion = COALESCE(fecha_actualizacion, CURRENT_TIMESTAMP), "
        "fecha_actualizacion = COALESCE(fecha_actualizacion, CURRENT_TIMESTAMP)"
    ))
    op.execute(sa.text(
        "UPDATE variantes SET fecha_creacion = COALESCE(fecha_actualizacion, CURRENT_TIMESTAMP), "
        "fecha_actualizacion = COALESCE(fecha_actualizacion, CURRENT_TIMESTAMP)"
    ))

    with op.batch_alter_table('tiendas') as batch_op:
        batch_op.alter_column('fecha_creacion', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('fecha_actualizacion', existing_type=sa.DateTime(), nullable=False)
    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column('fecha_creacion', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('fecha_actualizacion', existing_type=sa.DateTime(), nullable=False)
        batch_op.create_unique_constraint(
            'uq_producto_tienda_id_externo', ['tienda_id', 'id_externo']
        )
    with op.batch_alter_table('variantes') as batch_op:
        batch_op.alter_column('fecha_creacion', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('fecha_actualizacion', existing_type=sa.DateTime(), nullable=False)


def downgrade():
    with op.batch_alter_table('variantes') as batch_op:
        batch_op.drop_column('fecha_creacion')
    with op.batch_alter_table('productos') as batch_op:
        batch_op.drop_constraint('uq_producto_tienda_id_externo', type_='unique')
        batch_op.drop_column('fecha_creacion')
        batch_op.drop_column('id_externo')
    with op.batch_alter_table('tiendas') as batch_op:
        batch_op.drop_column('fecha_actualizacion')
        batch_op.drop_column('fecha_creacion')