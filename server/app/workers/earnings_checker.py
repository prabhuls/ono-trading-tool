"""
Earnings Checker Worker
Checks and updates earnings dates for TodaysMovers with weekly options
Updates upcoming_earnings flag for stocks with earnings within 14 days
"""

import logging
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movers import TodaysMover
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


class EarningsChecker:
    """Check and update earnings dates for today's movers with weekly options"""
    
    def __init__(self):
        self.updated_count = 0
        self.failed_count = 0
        self.failed_symbols = []
        self.earnings_threshold_days = 14  # Flag stocks with earnings within 14 days
    
    async def get_weekly_movers(self, session: AsyncSession) -> List[TodaysMover]:
        """Get all today's movers that have weekly options"""
        result = await session.execute(
            select(TodaysMover)
            .where(TodaysMover.has_weeklies == True)
            .order_by(TodaysMover.symbol)
        )
        return result.scalars().all()
    
    def fetch_earnings_date(self, symbol: str, retry_count: int = 0, max_retries: int = 3) -> Optional[datetime]:
        """Fetch next earnings date from yfinance with retry logic for rate limiting"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Try to get earnings dates
            try:
                earnings_dates = ticker.get_earnings_dates(limit=10)
                
                if earnings_dates is not None and not earnings_dates.empty:
                    today = datetime.now().date()
                    
                    # Find the next future earnings date
                    for date_idx in earnings_dates.index:
                        try:
                            # Convert pandas Timestamp to date
                            if hasattr(date_idx, 'date'):
                                earnings_date = date_idx.date()
                            elif hasattr(date_idx, 'to_pydatetime'):
                                earnings_date = date_idx.to_pydatetime().date()
                            else:
                                continue
                            
                            # Only consider future dates
                            if earnings_date >= today:
                                return datetime.combine(earnings_date, datetime.min.time())
                        except (AttributeError, TypeError):
                            continue
            except Exception:
                pass
            
            # Fallback: Try info method
            info = ticker.info
            earnings_timestamp = info.get('earningsTimestamp')
            if earnings_timestamp:
                earnings_date = datetime.fromtimestamp(earnings_timestamp)
                if earnings_date.date() >= datetime.now().date():
                    return earnings_date
            
            # Try calendar method as last resort
            try:
                calendar = ticker.calendar
                if calendar and not calendar.empty:
                    if 'Earnings Date' in calendar.columns:
                        earnings_dates = calendar['Earnings Date']
                        if not earnings_dates.empty and earnings_dates[0]:
                            return earnings_dates[0].to_pydatetime()
            except Exception:
                pass
            
            return None
            
        except Exception as e:
            # Check if it's a rate limit error (429) and retry if possible
            error_str = str(e)
            if ('429' in error_str or 'Too Many Requests' in error_str) and retry_count < max_retries:
                # Exponential backoff: 2, 4, 8 seconds
                wait_time = 2 ** (retry_count + 1)
                logger.warning(f"Rate limited on {symbol}, retrying in {wait_time} seconds (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(wait_time)
                return self.fetch_earnings_date(symbol, retry_count + 1, max_retries)
            
            logger.error(f"Error fetching earnings for {symbol}: {e}")
            return None
    
    def has_upcoming_earnings(self, earnings_date: Optional[datetime]) -> bool:
        """Check if earnings are within threshold days"""
        if not earnings_date:
            return False
        
        today = datetime.now().date()
        earnings_day = earnings_date.date()
        
        # Calculate days until earnings
        days_to_earnings = (earnings_day - today).days
        
        # Flag if earnings are within threshold (14 days)
        return 0 <= days_to_earnings <= self.earnings_threshold_days
    
    async def update_mover_earnings(
        self, 
        session: AsyncSession, 
        mover: TodaysMover, 
        has_upcoming: bool
    ) -> bool:
        """Update mover's upcoming_earnings flag in database"""
        try:
            # Update the mover record
            await session.execute(
                update(TodaysMover)
                .where(TodaysMover.id == mover.id)
                .values(
                    upcoming_earnings=has_upcoming,
                    last_updated=datetime.utcnow()
                )
            )
            
            logger.info(
                f"Updated {mover.symbol}: upcoming_earnings={has_upcoming}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating earnings for {mover.symbol}: {e}")
            return False
    
    async def process_batch(self, movers: List[TodaysMover]) -> Dict:
        """Process a batch of movers"""
        results = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
            'with_upcoming_earnings': 0,
            'details': []
        }
        
        async for session in get_async_session():
            for mover in movers:
                try:
                    # Add delay to avoid Yahoo Finance rate limiting (429 errors)
                    time.sleep(1)  # 1 second delay between requests
                    
                    # Fetch earnings date
                    earnings_date = self.fetch_earnings_date(mover.symbol)
                    has_upcoming = self.has_upcoming_earnings(earnings_date)
                    
                    # Check if update needed
                    needs_update = mover.upcoming_earnings != has_upcoming
                    
                    if needs_update:
                        success = await self.update_mover_earnings(
                            session, 
                            mover, 
                            has_upcoming
                        )
                        
                        if success:
                            results['updated'] += 1
                            self.updated_count += 1
                            if has_upcoming:
                                results['with_upcoming_earnings'] += 1
                        else:
                            results['failed'] += 1
                            self.failed_count += 1
                            self.failed_symbols.append(mover.symbol)
                    
                    results['processed'] += 1
                    
                    # Add to details
                    results['details'].append({
                        'symbol': mover.symbol,
                        'earnings_date': earnings_date.isoformat() if earnings_date else None,
                        'has_upcoming_earnings': has_upcoming,
                        'updated': needs_update
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing {mover.symbol}: {e}")
                    results['failed'] += 1
                    self.failed_count += 1
                    self.failed_symbols.append(mover.symbol)
            
            # Commit all changes
            await session.commit()
        
        return results
    
    async def run(self, batch_size: int = 20) -> Dict:
        """Run earnings check for all movers with weekly options"""
        logger.info("Starting Earnings Checker for Today's Movers...")
        
        start_time = datetime.utcnow()
        all_results = {
            'total_processed': 0,
            'total_updated': 0,
            'total_failed': 0,
            'total_with_upcoming_earnings': 0,
            'batches': [],
            'failed_symbols': []
        }
        
        try:
            # Get all movers with weekly options
            async for session in get_async_session():
                movers = await self.get_weekly_movers(session)
                logger.info(f"Found {len(movers)} movers with weekly options to check")
            
            if not movers:
                logger.info("No movers with weekly options found")
                all_results['message'] = "No movers with weekly options to check"
                return all_results
            
            # Process in batches (smaller batches to avoid rate limiting)
            for i in range(0, len(movers), batch_size):
                batch = movers[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} movers)")
                
                batch_results = await self.process_batch(batch)
                
                all_results['total_processed'] += batch_results['processed']
                all_results['total_updated'] += batch_results['updated']
                all_results['total_failed'] += batch_results['failed']
                all_results['total_with_upcoming_earnings'] += batch_results.get('with_upcoming_earnings', 0)
                all_results['batches'].append(batch_results)
            
            all_results['failed_symbols'] = self.failed_symbols
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log summary
            logger.info(f"Earnings Checker completed in {execution_time:.2f} seconds")
            logger.info(f"Total processed: {all_results['total_processed']}")
            logger.info(f"Total updated: {all_results['total_updated']}")
            logger.info(f"Total with upcoming earnings: {all_results['total_with_upcoming_earnings']}")
            logger.info(f"Total failed: {all_results['total_failed']}")
            
            if self.failed_symbols:
                logger.warning(f"Failed symbols: {', '.join(self.failed_symbols[:10])}")
            
            all_results['execution_time'] = execution_time
            all_results['timestamp'] = datetime.utcnow().isoformat()
            
            return all_results
            
        except Exception as e:
            logger.error(f"Earnings Checker failed: {e}")
            raise


async def check_earnings():
    """Main entry point for earnings checking"""
    checker = EarningsChecker()
    return await checker.run()


# Optional: Webhook integration
async def send_earnings_webhook(webhook_url: str = None):
    """
    Send earnings data to external webhook (if needed)
    This can be used to notify external systems about earnings updates
    """
    if not webhook_url:
        logger.info("No webhook URL configured, skipping webhook notification")
        return
    
    try:
        import aiohttp
        import json
        
        # Get movers with upcoming earnings
        async for session in get_async_session():
            result = await session.execute(
                select(TodaysMover)
                .where(
                    and_(
                        TodaysMover.has_weeklies == True,
                        TodaysMover.upcoming_earnings == True
                    )
                )
            )
            movers_with_earnings = result.scalars().all()
        
        # Format payload
        payload = {
            "data": [
                {
                    "ticker": mover.symbol,
                    "hasLessThan14daysToEarnings": True
                }
                for mover in movers_with_earnings
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send webhook
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent webhook with {len(payload['data'])} tickers")
                else:
                    logger.error(f"Webhook failed with status {response.status}")
                    
    except Exception as e:
        logger.error(f"Error sending webhook: {e}")