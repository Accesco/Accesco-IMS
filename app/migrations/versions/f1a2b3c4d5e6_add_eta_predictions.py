"""add eta_predictions table

Revision ID: f1a2b3c4d5e6
Revises: b5c7d9e1f2a3
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'b5c7d9e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'eta_predictions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('shipment_id', sa.String(50), nullable=True, index=True),
        sa.Column('lane_id', sa.String(50), nullable=False, index=True),
        sa.Column('carrier_id', sa.String(50), nullable=False, index=True),
        sa.Column('naive_eta_remaining_min', sa.Float(), nullable=False),
        sa.Column('predicted_drift_min', sa.Float(), nullable=False),
        sa.Column('corrected_eta_remaining_min', sa.Float(), nullable=False),
        sa.Column('current_speed_kmh', sa.Float(), nullable=False),
        sa.Column('distance_remaining_km', sa.Float(), nullable=False),
        sa.Column('is_rush_hour', sa.Boolean(), nullable=False),
        sa.Column('ml_response_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('eta_predictions')
