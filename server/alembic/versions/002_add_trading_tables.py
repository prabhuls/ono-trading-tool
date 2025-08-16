"""Add trading-specific tables for CashFlowAgent

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create stocks table
    op.create_table('stocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('last_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('trend_status', sa.String(length=20), nullable=False, server_default='neutral'),
        sa.Column('variability_52w', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('variability_monthly', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('variability_3day', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('passed_variability_check', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('special_character', sa.String(length=5), nullable=True),
        sa.Column('last_verified', sa.Date(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_stocks'),
        sa.UniqueConstraint('symbol', name='uq_stocks_symbol')
    )
    op.create_index('ix_stocks_symbol', 'stocks', ['symbol'], unique=True)
    op.create_index('ix_stocks_trend_status', 'stocks', ['trend_status'], unique=False)
    
    # Create historical_data table
    op.create_table('historical_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_historical_data')
    )
    op.create_index('ix_historical_data_symbol_date', 'historical_data', ['symbol', 'date'], unique=True)
    
    # Create ema_cache table
    op.create_table('ema_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('ema22', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema53', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema208', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_ema_cache')
    )
    op.create_index('ix_ema_cache_symbol_date', 'ema_cache', ['symbol', 'date'], unique=True)
    
    # Create main_lists table
    op.create_table('main_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('list_type', sa.String(length=20), nullable=False, comment='uptrend or downtrend'),
        sa.Column('last_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('variability_52w', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('variability_monthly', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('variability_3day', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('passed_variability_check', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('special_character', sa.String(length=5), nullable=True),
        sa.Column('added_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id', name='pk_main_lists')
    )
    op.create_index('ix_main_lists_symbol_list_type', 'main_lists', ['symbol', 'list_type'], unique=True)
    op.create_index('ix_main_lists_list_type', 'main_lists', ['list_type'], unique=False)
    op.create_index('ix_main_lists_is_active', 'main_lists', ['is_active'], unique=False)
    
    # Create todays_movers table
    op.create_table('todays_movers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('mover_type', sa.String(length=20), nullable=False, comment='uptrend or downtrend'),
        sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('price_change', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_change_percent', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('avg_volume', sa.BigInteger(), nullable=True),
        sa.Column('volume_ratio', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ema22', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema53', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema208', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema_strength', sa.Numeric(precision=10, scale=2), nullable=True, comment='Position relative to EMAs'),
        sa.Column('trend_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='Calculated trend strength'),
        sa.Column('market_cap', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('special_character', sa.String(length=5), nullable=True),
        sa.Column('passed_variability_check', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('options_expiring_10days', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('has_weeklies', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('has_earnings', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('earnings_date', sa.Date(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_todays_movers')
    )
    op.create_index('ix_todays_movers_symbol_mover_type', 'todays_movers', ['symbol', 'mover_type'], unique=True)
    op.create_index('ix_todays_movers_mover_type', 'todays_movers', ['mover_type'], unique=False)
    op.create_index('ix_todays_movers_has_weeklies', 'todays_movers', ['has_weeklies'], unique=False)
    op.create_index('ix_todays_movers_calculated_at', 'todays_movers', ['calculated_at'], unique=False)
    
    # Create credit_spreads table for structured trade storage
    op.create_table('credit_spreads',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('short_strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('long_strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('net_credit', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_risk', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('roi', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('expiration', sa.Date(), nullable=False),
        sa.Column('contract_type', sa.String(length=10), nullable=False, comment='call or put'),
        sa.Column('days_to_expiration', sa.Integer(), nullable=False),
        sa.Column('breakeven', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('buffer_room', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('scenarios', sa.JSON(), nullable=True, comment='Price scenarios JSON'),
        sa.Column('trade_status', sa.String(length=20), nullable=False, server_default='saved', comment='saved, claimed, closed'),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('profit_loss', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_credit_spreads_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_credit_spreads')
    )
    op.create_index('ix_credit_spreads_id', 'credit_spreads', ['id'], unique=False)
    op.create_index('ix_credit_spreads_user_id', 'credit_spreads', ['user_id'], unique=False)
    op.create_index('ix_credit_spreads_ticker', 'credit_spreads', ['ticker'], unique=False)
    op.create_index('ix_credit_spreads_trade_status', 'credit_spreads', ['trade_status'], unique=False)
    op.create_index('ix_credit_spreads_created_at', 'credit_spreads', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_credit_spreads_created_at', table_name='credit_spreads')
    op.drop_index('ix_credit_spreads_trade_status', table_name='credit_spreads')
    op.drop_index('ix_credit_spreads_ticker', table_name='credit_spreads')
    op.drop_index('ix_credit_spreads_user_id', table_name='credit_spreads')
    op.drop_index('ix_credit_spreads_id', table_name='credit_spreads')
    op.drop_table('credit_spreads')
    
    op.drop_index('ix_todays_movers_calculated_at', table_name='todays_movers')
    op.drop_index('ix_todays_movers_has_weeklies', table_name='todays_movers')
    op.drop_index('ix_todays_movers_mover_type', table_name='todays_movers')
    op.drop_index('ix_todays_movers_symbol_mover_type', table_name='todays_movers')
    op.drop_table('todays_movers')
    
    op.drop_index('ix_main_lists_is_active', table_name='main_lists')
    op.drop_index('ix_main_lists_list_type', table_name='main_lists')
    op.drop_index('ix_main_lists_symbol_list_type', table_name='main_lists')
    op.drop_table('main_lists')
    
    op.drop_index('ix_ema_cache_symbol_date', table_name='ema_cache')
    op.drop_table('ema_cache')
    
    op.drop_index('ix_historical_data_symbol_date', table_name='historical_data')
    op.drop_table('historical_data')
    
    op.drop_index('ix_stocks_trend_status', table_name='stocks')
    op.drop_index('ix_stocks_symbol', table_name='stocks')
    op.drop_table('stocks')