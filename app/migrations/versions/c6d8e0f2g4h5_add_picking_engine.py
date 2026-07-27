"""add picking engine

Revision ID: c6d8e0f2g4h5
Revises: b5c7d9e1f2a3
Create Date: 2026-07-26 11:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d8e0f2g4h5'
down_revision: Union[str, None] = 'b5c7d9e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create pick_waves table
    op.create_table('pick_waves',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pick_waves_id'), 'pick_waves', ['id'], unique=False)
    
    # create pick_tasks table
    op.create_table('pick_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wave_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['wave_id'], ['pick_waves.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pick_tasks_id'), 'pick_tasks', ['id'], unique=False)
    
    # create pick_task_items table
    op.create_table('pick_task_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pick_task_id', sa.Integer(), nullable=False),
        sa.Column('order_item_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('expected_quantity', sa.Integer(), nullable=False),
        sa.Column('picked_quantity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pick_task_id'], ['pick_tasks.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pick_task_items_id'), 'pick_task_items', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_pick_task_items_id'), table_name='pick_task_items')
    op.drop_table('pick_task_items')
    op.drop_index(op.f('ix_pick_tasks_id'), table_name='pick_tasks')
    op.drop_table('pick_tasks')
    op.drop_index(op.f('ix_pick_waves_id'), table_name='pick_waves')
    op.drop_table('pick_waves')
