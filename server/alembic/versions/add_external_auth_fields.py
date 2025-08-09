"""Add external auth fields to user model

Revision ID: add_external_auth_fields
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_external_auth_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add external_auth_id column
    op.add_column('users', sa.Column('external_auth_id', sa.String(length=255), nullable=True, comment='User ID from external auth provider (trading service)'))
    
    # Add subscription_data column
    op.add_column('users', sa.Column('subscription_data', sa.JSON(), nullable=True, comment="User's subscription data from trading service"))
    
    # Create unique index on external_auth_id
    op.create_index(op.f('ix_users_external_auth_id'), 'users', ['external_auth_id'], unique=True)


def downgrade() -> None:
    # Drop the index
    op.drop_index(op.f('ix_users_external_auth_id'), table_name='users')
    
    # Drop the columns
    op.drop_column('users', 'subscription_data')
    op.drop_column('users', 'external_auth_id')