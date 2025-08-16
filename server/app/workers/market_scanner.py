"""
Market Scanner Worker - 100% Match with PHP Implementation
Scans for 52-week highs/lows and validates with variability checks
"""

import logging
import asyncio
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stocks import Stock, HistoricalData, EMACache
from app.models.movers import TodaysMover, MainList
from app.core.database import get_async_session
from app.services.tradelist.client import TradeListClient

logger = logging.getLogger(__name__)


class MarketScanner:
    """Market scanner that matches PHP implementation exactly"""
    
    def __init__(self):
        self.tradelist_client = TradeListClient()
        self.blocked_stocks = self._load_blocked_stocks()
        self.verified_dir = Path("verified_today")
        self.verified_dir.mkdir(exist_ok=True)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.verified_highs_file = self.verified_dir / f"verified-highs-{self.current_date}.txt"
        self.verified_lows_file = self.verified_dir / f"verified-lows-{self.current_date}.txt"
        self.verified_highs_today = self._load_verified_symbols(self.verified_highs_file)
        self.verified_lows_today = self._load_verified_symbols(self.verified_lows_file)
        self.historical_data_cache = {}
        
    def _load_blocked_stocks(self) -> List[str]:
        """Load blocked stocks list"""
        blocked_file = Path("blockedstocks.txt")
        if blocked_file.exists():
            with open(blocked_file, 'r') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return []
    
    def _load_verified_symbols(self, filepath: Path) -> set:
        """Load verified symbols from file"""
        if filepath.exists():
            with open(filepath, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def _add_verified_symbol(self, symbol: str, is_high: bool):
        """Add symbol to verified file"""
        filepath = self.verified_highs_file if is_high else self.verified_lows_file
        verified_set = self.verified_highs_today if is_high else self.verified_lows_today
        
        if symbol not in verified_set:
            with open(filepath, 'a') as f:
                f.write(f"{symbol}\n")
            verified_set.add(symbol)
    
    async def get_highs_lows_lists(self) -> Tuple[List[str], List[str]]:
        """Fetch highs and lows lists from API - matches PHP exactly"""
        logger.info("Fetching highs and lows symbol lists from API")
        
        # Get highs with exact PHP parameters
        highs = await self.tradelist_client.get_highs_lows(
            extreme="high",
            price=15.0,
            volume=500000
        )
        
        # Get lows with exact PHP parameters  
        lows = await self.tradelist_client.get_highs_lows(
            extreme="low",
            price=15.0,
            volume=500000
        )
        
        logger.info(f"Fetched {len(highs)} highs and {len(lows)} lows")
        return highs, lows
    
    async def get_ohlcv_data(self, symbol: str) -> Optional[Dict]:
        """Get OHLCV data - fallback to historical if current day fails"""
        # Try to get current day data first
        historical = await self.tradelist_client.get_historical_data(symbol, days=1)
        if historical and len(historical) > 0:
            latest = historical[0]
            return {
                'open': float(latest.get('o', 0)),
                'high': float(latest.get('h', 0)),
                'low': float(latest.get('l', 0)),
                'close': float(latest.get('c', 0)),
                'volume': int(latest.get('v', 0)),
                'adj_close': float(latest.get('c', 0))
            }
        
        # Fallback: Use cached historical data if available (like PHP does)
        cached_historical = self.historical_data_cache.get(symbol)
        if cached_historical and cached_historical.get('tradingDays'):
            latest_day = cached_historical['tradingDays'][0]  # Most recent day
            return {
                'open': float(latest_day.get('close', 0)),  # PHP uses close as open
                'high': float(latest_day.get('high', 0)),
                'low': float(latest_day.get('low', 0)),
                'close': float(latest_day.get('close', 0)),
                'volume': int(latest_day.get('volume', 0)),
                'adj_close': float(latest_day.get('close', 0))
            }
        
        # Last resort: Try to load historical data
        historical_data = await self.get_complete_historical_data(symbol)
        if historical_data and historical_data.get('tradingDays'):
            latest_day = historical_data['tradingDays'][0]
            return {
                'open': float(latest_day.get('close', 0)),
                'high': float(latest_day.get('high', 0)),
                'low': float(latest_day.get('low', 0)),
                'close': float(latest_day.get('close', 0)),
                'volume': int(latest_day.get('volume', 0)),
                'adj_close': float(latest_day.get('close', 0))
            }
        
        return None
    
    async def get_52week_stats(self, symbol: str) -> Optional[Dict]:
        """Get 52-week stats from historical data (skip failing endpoints)"""
        # Calculate directly from historical data since quote/stock_info endpoints don't work
        historical = await self.get_complete_historical_data(symbol)
        if historical and 'stats' in historical:
            return historical['stats']
        
        return None
    
    async def get_complete_historical_data(self, symbol: str) -> Optional[Dict]:
        """Get complete historical data with caching - matches PHP"""
        # Check cache
        if symbol in self.historical_data_cache:
            return self.historical_data_cache[symbol]
        
        # Fetch from API (PHP fetches 1 year + 3 days)
        historical = await self.tradelist_client.get_historical_data(symbol, days=365)
        if not historical or len(historical) < 5:
            return None
        
        # Process into trading days format
        trading_days = []
        for result in historical:
            if 't' in result and 'c' in result and 'v' in result:
                trading_days.append({
                    'date': datetime.fromtimestamp(result['t'] / 1000).strftime('%Y-%m-%d'),
                    'close': float(result['c']),
                    'volume': int(result['v']),
                    'high': float(result['h']),
                    'low': float(result['l'])
                })
        
        if len(trading_days) < 5:
            return None
        
        # Sort by date (newest first) - PHP uses desc sort
        trading_days.sort(key=lambda x: x['date'], reverse=True)
        
        # Calculate stats
        highs = [d['high'] for d in trading_days]
        lows = [d['low'] for d in trading_days]
        volumes = [d['volume'] for d in trading_days]
        
        highest_52w = max(highs) if highs else 0
        lowest_52w = min(lows) if lows else 0
        avgvol = sum(volumes) / len(volumes) if volumes else 0
        
        # Get current day data
        current_day = trading_days[0] if trading_days else None
        current_high = current_day['high'] if current_day else 0
        current_low = current_day['low'] if current_day else 0
        
        # Filter for monthly data (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        monthly_data = [d for d in trading_days if d['date'] >= thirty_days_ago]
        
        # Get last 3 days
        three_day_data = trading_days[:3] if len(trading_days) >= 3 else trading_days
        
        result = {
            'tradingDays': trading_days,
            'stats': {
                'highest_52w': highest_52w,
                'lowest_52w': lowest_52w,
                'avgvol': int(avgvol),
                'current_high': current_high,
                'current_low': current_low
            },
            'monthlyData': monthly_data,
            'threeDayData': three_day_data,
            'currentDayData': current_day
        }
        
        # Cache it
        self.historical_data_cache[symbol] = result
        return result
    
    def check_variability(self, symbol: str, stats: Dict) -> bool:
        """Check variability matching PHP thresholds exactly"""
        historical_data = self.historical_data_cache.get(symbol)
        if not historical_data or not historical_data.get('tradingDays'):
            logger.warning(f"{symbol}: Cannot check variability, no historical data")
            return False
        
        # Annual variability check (using API stats)
        annual_high = float(stats.get('highest_52w', 0))
        annual_low = float(stats.get('lowest_52w', 0))
        
        if annual_low <= 0:
            logger.warning(f"{symbol}: Annual variability FAIL - Invalid 52w Low: {annual_low}")
            return False
        
        if annual_high < annual_low:
            logger.warning(f"{symbol}: Annual variability FAIL - 52w High < Low ({annual_high} < {annual_low})")
            return False
        
        annual_var = ((annual_high - annual_low) / annual_low) * 100
        annual_check = (annual_var >= 30 and annual_var <= 200)  # PHP thresholds
        
        # Monthly variability check
        monthly_data = historical_data.get('monthlyData', [])
        if len(monthly_data) < 5:
            logger.warning(f"{symbol}: Monthly variability FAIL - Insufficient data: {len(monthly_data)}")
            return False
        
        monthly_highs = [d['high'] for d in monthly_data]
        monthly_lows = [d['low'] for d in monthly_data]
        monthly_high = max(monthly_highs)
        monthly_low = min(monthly_lows)
        
        if monthly_low <= 0:
            logger.warning(f"{symbol}: Monthly variability FAIL - Invalid monthly low")
            return False
        
        monthly_var = ((monthly_high - monthly_low) / monthly_low) * 100
        monthly_check = (monthly_var >= 8 and monthly_var <= 80)  # PHP thresholds
        
        # 3-day variability check
        three_day_data = historical_data.get('threeDayData', [])
        if len(three_day_data) < 3:
            logger.warning(f"{symbol}: 3-day variability FAIL - Insufficient data: {len(three_day_data)}")
            return False
        
        three_day_highs = [d['high'] for d in three_day_data]
        three_day_lows = [d['low'] for d in three_day_data]
        three_day_high = max(three_day_highs)
        three_day_low = min(three_day_lows)
        
        if three_day_low <= 0:
            logger.warning(f"{symbol}: 3-day variability FAIL - Invalid 3-day low")
            return False
        
        three_day_var = ((three_day_high - three_day_low) / three_day_low) * 100
        three_day_check = (three_day_var >= 3 and three_day_var <= 30)  # PHP thresholds
        
        passed = annual_check and monthly_check and three_day_check
        
        logger.info(f"{symbol} variability checks:")
        logger.info(f"  Annual: {annual_var:.2f}% {'PASS' if annual_check else 'FAIL'}")
        logger.info(f"  Monthly: {monthly_var:.2f}% {'PASS' if monthly_check else 'FAIL'}")
        logger.info(f"  3-Day: {three_day_var:.2f}% {'PASS' if three_day_check else 'FAIL'}")
        logger.info(f"  Overall: {'PASS' if passed else 'FAIL'}")
        
        return passed
    
    def check_price_history(self, symbol: str, is_high: bool) -> str:
        """Check price history for special character marking - matches PHP"""
        historical_data = self.historical_data_cache.get(symbol)
        if not historical_data or not historical_data.get('tradingDays'):
            return ''
        
        trading_days = historical_data['tradingDays']  # Newest first
        today = datetime.now()
        
        # PHP intervals
        intervals = [14, 28, 42, 56, 91, 140] if is_high else [14, 35, 56, 77, 98]
        prices = {}
        trading_day_index = 0
        
        for target_days_ago in intervals:
            found_price = False
            for i in range(trading_day_index, len(trading_days)):
                day_date = datetime.strptime(trading_days[i]['date'], '%Y-%m-%d')
                days_diff = (today - day_date).days
                if days_diff >= target_days_ago:
                    prices[target_days_ago] = trading_days[i]['close']
                    trading_day_index = i + 1
                    found_price = True
                    break
            
            if not found_price:
                return ''  # Cannot meet condition
        
        # Check conditions
        if is_high:
            # For highs: prices should be ascending (recent > older)
            if all(k in prices for k in [14, 28, 42, 56, 91, 140]):
                if (prices[14] > prices[28] and prices[28] > prices[42] and 
                    prices[42] > prices[56] and prices[56] > prices[91] and 
                    prices[91] > prices[140]):
                    return '*'
        else:
            # For lows: prices should be descending (recent < older)
            if all(k in prices for k in [14, 35, 56, 77, 98]):
                if (prices[14] < prices[35] and prices[35] < prices[56] and 
                    prices[56] < prices[77] and prices[77] < prices[98]):
                    return '▼'
        
        return ''
    
    async def get_options_analysis(self, symbol: str) -> Dict:
        """Get options analysis matching PHP exactly"""
        contracts = await self.tradelist_client.get_options_contracts(symbol, limit=1000)
        
        if not contracts:
            return {'options_expiring_10days': 0, 'has_weeklies': False}
        
        today = datetime.now()
        ten_days_from_now = today + timedelta(days=10)
        expiring_contracts = 0
        expiration_dates = []
        
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            
            # Get expiration date (PHP uses 'expiration_date' field)
            exp_date_str = contract.get('expiration_date')
            if not exp_date_str:
                # Try other field names
                for field in ['expiration', 'exp_date', 'expirationDate', 'expiry', 'expire_date']:
                    if field in contract:
                        exp_date_str = contract[field]
                        break
            
            if not exp_date_str:
                continue
            
            try:
                # Parse date
                if isinstance(exp_date_str, (int, float)):
                    # Unix timestamp
                    if exp_date_str > 10000000000:  # Milliseconds
                        exp_date_str = exp_date_str / 1000
                    exp_date = datetime.fromtimestamp(exp_date_str)
                else:
                    exp_date = datetime.strptime(str(exp_date_str), '%Y-%m-%d')
                
                # Count if expiring within 10 days
                if today <= exp_date <= ten_days_from_now:
                    expiring_contracts += 1
                
                # Collect unique expiration dates
                date_key = exp_date.strftime('%Y-%m-%d')
                if date_key not in expiration_dates:
                    expiration_dates.append(date_key)
                    
            except Exception as e:
                logger.debug(f"Failed to parse expiration date for {symbol}: {exp_date_str}")
                continue
        
        # Detect weekly options (PHP logic)
        has_weeklies = self._detect_weekly_options(expiration_dates)
        
        logger.info(f"Options for {symbol}: {expiring_contracts} expiring in 10 days, weeklies: {has_weeklies}")
        
        return {
            'options_expiring_10days': expiring_contracts,
            'has_weeklies': has_weeklies
        }
    
    def _detect_weekly_options(self, expiration_dates: List[str]) -> bool:
        """Detect weekly options matching PHP logic"""
        if len(expiration_dates) < 3:
            return False
        
        # Sort dates
        expiration_dates.sort()
        today = datetime.now()
        
        # Get future expirations within 60 days
        future_expirations = []
        for date_str in expiration_dates:
            try:
                exp_date = datetime.strptime(date_str, '%Y-%m-%d')
                days_from_today = (exp_date - today).days
                if 0 <= days_from_today <= 60:
                    future_expirations.append(exp_date)
            except:
                continue
        
        if len(future_expirations) < 3:
            return False
        
        # Calculate gaps between consecutive dates
        gaps = []
        for i in range(1, len(future_expirations)):
            gap = (future_expirations[i] - future_expirations[i-1]).days
            gaps.append(gap)
        
        if not gaps:
            return False
        
        # Check for weekly pattern (PHP logic)
        weekly_gaps = [g for g in gaps if 6 <= g <= 8]
        short_gaps = [g for g in gaps if 1 <= g <= 3]  # Holiday adjustments
        total_weeklyish_gaps = len(weekly_gaps) + len(short_gaps)
        
        # Must have at least 2 weekly-ish gaps
        if total_weeklyish_gaps >= 2:
            return True
        
        # Fallback check
        large_gaps = [g for g in gaps if g > 10]
        seven_day_gaps = [g for g in gaps if g <= 7]
        
        if len(large_gaps) == 0 and len(seven_day_gaps) >= 2:
            return True
        
        return False
    
    async def process_symbol(
        self,
        session: AsyncSession,
        symbol: str,
        is_high: bool
    ) -> Dict:
        """Process individual symbol matching PHP logic exactly"""
        result = {
            'symbol': symbol,
            'processed': False,
            'skipped_reason': None,
            'error': None
        }
        
        # Check if blocked
        if symbol in self.blocked_stocks:
            result['skipped_reason'] = 'blocked'
            return result
        
        # Try to get historical data first (needed for everything)
        historical = await self.get_complete_historical_data(symbol)
        if not historical or not historical.get('tradingDays'):
            result['error'] = 'No historical data available (likely ETF or unsupported ticker)'
            logger.info(f"{symbol}: Skipping - no historical data available")
            return result
        
        # Get OHLCV from historical data
        ohlcv = await self.get_ohlcv_data(symbol)
        if not ohlcv:
            # Use latest from historical as fallback
            if historical and historical.get('tradingDays'):
                latest_day = historical['tradingDays'][0]
                ohlcv = {
                    'open': float(latest_day.get('close', 0)),
                    'high': float(latest_day.get('high', 0)),
                    'low': float(latest_day.get('low', 0)),
                    'close': float(latest_day.get('close', 0)),
                    'volume': int(latest_day.get('volume', 0)),
                    'adj_close': float(latest_day.get('close', 0))
                }
            else:
                result['error'] = 'Failed to fetch OHLCV data'
                return result
        
        # Get 52-week stats from historical
        stats = historical.get('stats')
        if not stats:
            result['error'] = 'Failed to calculate 52-week stats'
            return result
        
        # Check if already verified today
        verified_set = self.verified_highs_today if is_high else self.verified_lows_today
        is_verified_today = symbol in verified_set
        
        # Check variability (skip if already verified)
        if not is_verified_today:
            # Historical data already loaded above
            if not self.check_variability(symbol, stats):
                result['skipped_reason'] = 'variability'
                return result
            
            # Add to verified list
            self._add_verified_symbol(symbol, is_high)
        
        # Check price history for special character
        special_char = self.check_price_history(symbol, is_high)
        
        # Get options analysis
        options_analysis = await self.get_options_analysis(symbol)
        
        # Update database (todays_movers table)
        mover_type = 'uptrend' if is_high else 'downtrend'
        
        try:
            # Check if exists
            existing = await session.execute(
                select(TodaysMover).where(
                    and_(
                        TodaysMover.symbol == symbol,
                        TodaysMover.mover_type == mover_type
                    )
                )
            )
            mover = existing.scalar_one_or_none()
            
            if mover:
                # Update existing
                mover.current_price = Decimal(str(ohlcv['close']))
                mover.volume = ohlcv['volume']
                mover.special_character = special_char
                mover.options_expiring_10days = options_analysis['options_expiring_10days']
                mover.has_weeklies = options_analysis['has_weeklies']
                mover.last_updated = datetime.utcnow()
            else:
                # Create new
                mover = TodaysMover(
                    symbol=symbol,
                    name='',  # PHP doesn't set name
                    mover_type=mover_type,
                    current_price=Decimal(str(ohlcv['close'])),
                    volume=ohlcv['volume'],
                    special_character=special_char,
                    options_expiring_10days=options_analysis['options_expiring_10days'],
                    has_weeklies=options_analysis['has_weeklies'],
                    passed_variability_check=True,  # Passed if we got here
                    last_updated=datetime.utcnow(),
                    calculated_at=datetime.utcnow()
                )
                session.add(mover)
            
            result['processed'] = True
            result['special_char'] = special_char
            result['options_10days'] = options_analysis['options_expiring_10days']
            result['has_weeklies'] = options_analysis['has_weeklies']
            
        except Exception as e:
            logger.error(f"Database error for {symbol}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def run(self) -> Dict:
        """Run market scanner matching PHP flow exactly"""
        logger.info("Starting Market Scanner (PHP-matched implementation)")
        
        start_time = datetime.utcnow()
        results = {
            'highs_processed': 0,
            'lows_processed': 0,
            'highs_skipped_variability': 0,
            'lows_skipped_variability': 0,
            'highs_skipped_blocked': 0,
            'lows_skipped_blocked': 0,
            'highs_errors': 0,
            'lows_errors': 0,
            'total_in_database': 0
        }
        
        try:
            # Phase 1: Fetch highs and lows lists
            highs, lows = await self.get_highs_lows_lists()
            
            if not highs and not lows:
                logger.warning("No highs or lows fetched from API")
                return results
            
            logger.info(f"Processing {len(highs)} highs and {len(lows)} lows")
            
            async for session in get_async_session():
                # Check for market prep time (9:00-9:20 AM ET) - PHP truncates tables
                eastern_time = datetime.now()  # Adjust for your timezone
                if eastern_time.hour == 9 and eastern_time.minute <= 20:
                    logger.info("Market prep time - truncating todays_movers table")
                    await session.execute(delete(TodaysMover))
                    # Clear verified files
                    self.verified_highs_today.clear()
                    self.verified_lows_today.clear()
                    if self.verified_highs_file.exists():
                        self.verified_highs_file.unlink()
                    if self.verified_lows_file.exists():
                        self.verified_lows_file.unlink()
                
                # Process highs
                for i, symbol in enumerate(highs):
                    logger.info(f"Processing HIGH [{i+1}/{len(highs)}] {symbol}")
                    
                    result = await self.process_symbol(session, symbol, is_high=True)
                    
                    if result['processed']:
                        results['highs_processed'] += 1
                    elif result['skipped_reason'] == 'variability':
                        results['highs_skipped_variability'] += 1
                    elif result['skipped_reason'] == 'blocked':
                        results['highs_skipped_blocked'] += 1
                    elif result['error']:
                        results['highs_errors'] += 1
                    
                    # Garbage collection every 50 symbols (PHP does this)
                    if (i + 1) % 50 == 0:
                        await asyncio.sleep(0)  # Yield control
                
                # Process lows
                for i, symbol in enumerate(lows):
                    logger.info(f"Processing LOW [{i+1}/{len(lows)}] {symbol}")
                    
                    result = await self.process_symbol(session, symbol, is_high=False)
                    
                    if result['processed']:
                        results['lows_processed'] += 1
                    elif result['skipped_reason'] == 'variability':
                        results['lows_skipped_variability'] += 1
                    elif result['skipped_reason'] == 'blocked':
                        results['lows_skipped_blocked'] += 1
                    elif result['error']:
                        results['lows_errors'] += 1
                    
                    # Garbage collection every 50 symbols
                    if (i + 1) % 50 == 0:
                        await asyncio.sleep(0)  # Yield control
                
                # Commit all changes
                await session.commit()
                
                # Count total in database
                count_result = await session.execute(
                    select(TodaysMover)
                )
                results['total_in_database'] = len(count_result.scalars().all())
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log summary
            logger.info(f"Market Scanner completed in {execution_time:.2f} seconds")
            logger.info(f"Highs processed: {results['highs_processed']}")
            logger.info(f"Lows processed: {results['lows_processed']}")
            logger.info(f"Highs skipped (variability): {results['highs_skipped_variability']}")
            logger.info(f"Lows skipped (variability): {results['lows_skipped_variability']}")
            logger.info(f"Total in database: {results['total_in_database']}")
            
            results['execution_time'] = execution_time
            results['timestamp'] = datetime.utcnow().isoformat()
            
            return results
            
        except Exception as e:
            logger.error(f"Market Scanner failed: {e}")
            raise


async def scan_market():
    """Main entry point for market scanning"""
    scanner = MarketScanner()
    return await scanner.run()