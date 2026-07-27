"""add notifications table

Revision ID: b5c7d9e1f2a3
Revises: a3f8e2c1d4b7
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b5c7d9e1f2a3'
down_revision = 'a3f8e2c1d4b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='NORMAL'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.String(length=1000), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reference_type', sa.String(length=100), nullable=True),
        sa.Column('reference_id', sa.String(length=255), nullable=True),
        sa.Column('metadata_info', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_priority'), 'notifications', ['priority'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_reference_id'), 'notifications', ['reference_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_reference_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_priority'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
