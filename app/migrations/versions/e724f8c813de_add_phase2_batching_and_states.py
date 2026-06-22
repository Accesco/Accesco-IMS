"""add_phase2_batching_and_states

Revision ID: e724f8c813de
Revises: 6e07f6a120e7
Create Date: 2026-06-16 17:15:09.067674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e724f8c813de'
down_revision: Union[str, None] = '6e07f6a120e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Create communities and batches tables first
    op.create_table(
        'communities',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('centroid_latitude', sa.Float(), nullable=False),
        sa.Column('centroid_longitude', sa.Float(), nullable=False),
        sa.Column('polygon', sa.JSON(), nullable=False),
        sa.Column('entry_points', sa.JSON(), nullable=False),
        sa.Column('avg_walk_time_min', sa.Float(), nullable=False),
        sa.Column('batch_window_sec', sa.Integer(), nullable=False),
        sa.Column('max_batch_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('community_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=True),
        sa.Column('offered_rider_id', sa.Integer(), nullable=True),
        sa.Column('dispatch_by', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assignment_offered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.id'], ),
        sa.ForeignKeyConstraint(['offered_rider_id'], ['riders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Add columns to orders as nullable=True first (prevents pg NotNullViolationError)
    op.add_column('orders', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('delivery_zone', sa.String(length=20), nullable=True))
    op.add_column('orders', sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('community_id', sa.String(length=100), nullable=True))
    op.add_column('orders', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('offered_rider_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('assignment_offered_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Populate default values for existing Phase 1 orders (uses Bangalore coordinates as default)
    op.execute("UPDATE orders SET latitude = 12.9716 WHERE latitude IS NULL")
    op.execute("UPDATE orders SET longitude = 77.5946 WHERE longitude IS NULL")
    op.execute("UPDATE orders SET delivery_zone = 'ZONE_A' WHERE delivery_zone IS NULL")
    op.execute("UPDATE orders SET sla_deadline = NOW() WHERE sla_deadline IS NULL")

    # 4. Alter columns to be NOT NULL now that they contain default values
    op.alter_column('orders', 'latitude', nullable=False)
    op.alter_column('orders', 'longitude', nullable=False)
    op.alter_column('orders', 'delivery_zone', nullable=False)
    op.alter_column('orders', 'sla_deadline', nullable=False)

    # 5. Add columns to riders as nullable=True first
    op.add_column('riders', sa.Column('battery_level', sa.Float(), nullable=True))
    op.add_column('riders', sa.Column('shift_end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('riders', sa.Column('performance_score', sa.Float(), nullable=True))
    op.add_column('riders', sa.Column('consecutive_declines', sa.Integer(), nullable=True))
    op.add_column('riders', sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True))

    # 6. Populate default values for existing riders
    op.execute("UPDATE riders SET battery_level = 100.0 WHERE battery_level IS NULL")
    op.execute("UPDATE riders SET shift_end_time = NOW() + INTERVAL '8 hours' WHERE shift_end_time IS NULL")
    op.execute("UPDATE riders SET performance_score = 1.0 WHERE performance_score IS NULL")
    op.execute("UPDATE riders SET consecutive_declines = 0 WHERE consecutive_declines IS NULL")
    op.execute("UPDATE riders SET last_heartbeat_at = NOW() WHERE last_heartbeat_at IS NULL")

    # 7. Alter columns to be NOT NULL
    op.alter_column('riders', 'battery_level', nullable=False)
    op.alter_column('riders', 'shift_end_time', nullable=False)
    op.alter_column('riders', 'performance_score', nullable=False)
    op.alter_column('riders', 'consecutive_declines', nullable=False)
    op.alter_column('riders', 'last_heartbeat_at', nullable=False)

    # 8. Add nullable columns to stores
    op.add_column('stores', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('stores', sa.Column('longitude', sa.Float(), nullable=True))

    # 9. Create Foreign Key Constraints
    op.create_foreign_key('fk_orders_community', 'orders', 'communities', ['community_id'], ['id'])
    op.create_foreign_key('fk_orders_batch', 'orders', 'batches', ['batch_id'], ['id'])
    op.create_foreign_key('fk_orders_offered_rider', 'orders', 'riders', ['offered_rider_id'], ['id'])

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('stores', 'longitude')
    op.drop_column('stores', 'latitude')
    op.drop_column('riders', 'last_heartbeat_at')
    op.drop_column('riders', 'consecutive_declines')
    op.drop_column('riders', 'performance_score')
    op.drop_column('riders', 'shift_end_time')
    op.drop_column('riders', 'battery_level')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_column('orders', 'assignment_offered_at')
    op.drop_column('orders', 'offered_rider_id')
    op.drop_column('orders', 'batch_id')
    op.drop_column('orders', 'community_id')
    op.drop_column('orders', 'sla_deadline')
    op.drop_column('orders', 'delivery_zone')
    op.drop_column('orders', 'longitude')
    op.drop_column('orders', 'latitude')
    op.drop_index(op.f('ix_batches_id'), table_name='batches')
    op.drop_table('batches')
    op.drop_index(op.f('ix_communities_id'), table_name='communities')
    op.drop_table('communities')
    # ### end Alembic commands ###
