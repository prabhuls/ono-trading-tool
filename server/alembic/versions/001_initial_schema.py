"""Initial schema with users, api_keys, and watchlists

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.Text(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_users')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='User-friendly name for the API key'),
        sa.Column('service_name', sa.String(length=100), nullable=False, comment='Service identifier (polygon, alpaca, binance, etc.)'),
        sa.Column('encrypted_key', sa.Text(), nullable=False, comment='Encrypted API key value'),
        sa.Column('encrypted_secret', sa.Text(), nullable=True, comment='Encrypted API secret (if applicable)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional description or notes'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Last time this API key was used'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_api_keys_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_api_keys'),
        sa.UniqueConstraint('user_id', 'name', name='uq_api_keys_user_id_name')
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'], unique=False)
    op.create_index('ix_api_keys_service_name', 'api_keys', ['service_name'], unique=False)
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'], unique=False)
    
    # Create watchlists table
    op.create_table('watchlists',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Watchlist name'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='Optional description'),
        sa.Column('symbols', sa.JSON(), nullable=False, comment='Array of symbol objects with metadata'),
        sa.Column('symbol_count', sa.Integer(), nullable=False, comment='Number of symbols in watchlist'),
        sa.Column('is_public', sa.Boolean(), nullable=False, comment='Whether this watchlist is publicly visible'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_watchlists_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_watchlists'),
        sa.UniqueConstraint('user_id', 'name', name='uq_watchlists_user_id_name')
    )
    op.create_index('ix_watchlists_id', 'watchlists', ['id'], unique=False)
    op.create_index('ix_watchlists_user_id', 'watchlists', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_watchlists_user_id', table_name='watchlists')
    op.drop_index('ix_watchlists_id', table_name='watchlists')
    op.drop_table('watchlists')
    
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_index('ix_api_keys_service_name', table_name='api_keys')
    op.drop_index('ix_api_keys_id', table_name='api_keys')
    op.drop_table('api_keys')
    
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')