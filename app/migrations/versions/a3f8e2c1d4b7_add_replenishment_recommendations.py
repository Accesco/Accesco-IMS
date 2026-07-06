"""add replenishment_recommendations table

Revision ID: a3f8e2c1d4b7
Revises:
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3f8e2c1d4b7'
down_revision = 'e724f8c813df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'replenishment_recommendations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sku_id', sa.String(50), nullable=False),
        sa.Column('recommended_quantity', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING', index=True),
        sa.Column('purchase_order_id', sa.Integer(), sa.ForeignKey('purchase_orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('ml_response_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('replenishment_recommendations')
