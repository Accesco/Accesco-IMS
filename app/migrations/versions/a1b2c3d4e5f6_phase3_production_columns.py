"""Phase 3 production completion columns

Revision ID: a1b2c3d4e5f6
Revises: e724f8c813de


Adds:
  - orders.picking_started_at   
  - orders.assignment_was_optimal    
  - orders.actual_delivered_at       
  - riders.mandatory_assignment_flag  
  - riders.shift_active_seconds      
  - batches.actual_batch_size        
  - dispatch_latency_samples table    
  - forecast_metrics table            
  - community_dynamic_windows table   
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e724f8c813de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('picking_started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('assignment_was_optimal', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('actual_delivered_at', sa.DateTime(timezone=True), nullable=True))

    #  riders 
    with op.batch_alter_table('riders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mandatory_assignment_flag', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('shift_active_seconds', sa.Float(), nullable=False, server_default='0.0'))

    # batches
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('actual_batch_size', sa.Integer(), nullable=True))

    # dispatch_latency_samples
    op.create_table(
        'dispatch_latency_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(length=100), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dispatch_latency_samples_id', 'dispatch_latency_samples', ['id'], unique=False)
    op.create_index('ix_dispatch_latency_samples_path', 'dispatch_latency_samples', ['path'], unique=False)

    # forecast_metrics 
    op.create_table(
        'forecast_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('target_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('predicted_orders_per_min', sa.Float(), nullable=False),
        sa.Column('predicted_rider_demand', sa.Integer(), nullable=False),
        sa.Column('predicted_batch_size', sa.Float(), nullable=False),
        sa.Column('recommended_batch_window_sec', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_forecast_metrics_id', 'forecast_metrics', ['id'], unique=False)
    op.create_index('ix_forecast_metrics_store_id', 'forecast_metrics', ['store_id'], unique=False)
    op.create_index('ix_forecast_metrics_target_time', 'forecast_metrics', ['target_time'], unique=False)

    # community_dynamic_windows 
    op.create_table(
        'community_dynamic_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('community_id', sa.String(length=100), nullable=False),
        sa.Column('hour_of_day', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('order_velocity_weight', sa.Float(), nullable=False),
        sa.Column('calculated_window_sec', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_community_dynamic_windows_id', 'community_dynamic_windows', ['id'], unique=False)
    op.create_index('ix_community_dynamic_windows_community_id', 'community_dynamic_windows', ['community_id'], unique=False)


def downgrade() -> None:
    op.drop_table('community_dynamic_windows')
    op.drop_table('forecast_metrics')
    op.drop_table('dispatch_latency_samples')

    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.drop_column('actual_batch_size')

    with op.batch_alter_table('riders', schema=None) as batch_op:
        batch_op.drop_column('shift_active_seconds')
        batch_op.drop_column('mandatory_assignment_flag')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('actual_delivered_at')
        batch_op.drop_column('assignment_was_optimal')
        batch_op.drop_column('picking_started_at')
