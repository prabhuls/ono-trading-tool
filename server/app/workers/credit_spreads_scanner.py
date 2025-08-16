"""
Credit Spreads Scanner Worker
Scans todays_movers for tickers with weekly options and analyzes credit spread opportunities
Updates has_spreads field based on results
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movers import TodaysMover
from app.core.database import get_async_session
from app.services.credit_spread_detector import CreditSpreadDetector

logger = logging.getLogger(__name__)


class CreditSpreadsScanner:
    """Scanner for credit spread opportunities on weekly options"""
    
    def __init__(self):
        self.processed_count = 0
        self.spreads_found = 0
        self.failed_symbols = []
        
    async def get_weekly_tickers(self, session: AsyncSession) -> List[TodaysMover]:
        """Get all tickers from todays_movers that have weekly options"""
        result = await session.execute(
            select(TodaysMover).where(
                TodaysMover.has_weeklies == True
            )
        )
        return result.scalars().all()
    
    async def analyze_ticker_for_spreads(
        self,
        ticker: TodaysMover,
        detector: CreditSpreadDetector
    ) -> Optional[Dict]:
        """Analyze a single ticker for credit spread opportunities"""
        try:
            symbol = ticker.symbol
            mover_type = ticker.mover_type
            current_price = float(ticker.current_price)
            
            # Map mover_type to trend
            # uptrend = bullish = put credit spreads
            # downtrend = bearish = call credit spreads
            trend = 'uptrend' if mover_type == 'uptrend' else 'downtrend'
            
            logger.info(f"Analyzing {symbol} ({mover_type}) for credit spreads at ${current_price}")
            
            # Run credit spread analysis
            spread_result = await detector.find_best_credit_spread(symbol, current_price, trend)
            
            if spread_result and spread_result.get('found'):
                logger.info(f"✓ Found credit spread for {symbol}: {spread_result.get('roi_percent', 0):.1f}% ROI")
                return {
                    'symbol': symbol,
                    'has_spread': True,
                    'spread_data': spread_result
                }
            else:
                reason = spread_result.get('reason', 'Unknown')
                logger.info(f"✗ No spread for {symbol}: {reason}")
                return {
                    'symbol': symbol,
                    'has_spread': False,
                    'reason': reason
                }
                
        except Exception as e:
            logger.error(f"Error analyzing {ticker.symbol}: {str(e)}")
            self.failed_symbols.append(ticker.symbol)
            return None
    
    async def update_database_results(
        self,
        session: AsyncSession,
        results: List[Dict]
    ):
        """Update has_spreads field in database based on results"""
        try:
            # Get symbols that have spreads
            symbols_with_spreads = [r['symbol'] for r in results if r and r.get('has_spread')]
            
            # Update records with spreads
            if symbols_with_spreads:
                await session.execute(
                    update(TodaysMover)
                    .where(TodaysMover.symbol.in_(symbols_with_spreads))
                    .values(has_spreads=True)
                )
                logger.info(f"Updated {len(symbols_with_spreads)} tickers with has_spreads=True")
            
            # Set has_spreads=False for ALL other tickers
            await session.execute(
                update(TodaysMover)
                .where(~TodaysMover.symbol.in_(symbols_with_spreads))
                .values(has_spreads=False)
            )
            
            # Count total records
            count_result = await session.execute(select(TodaysMover))
            total_records = len(count_result.scalars().all())
            
            logger.info(f"Set has_spreads=False for {total_records - len(symbols_with_spreads)} tickers")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Database update error: {e}")
            await session.rollback()
            raise
    
    async def run(self) -> Dict:
        """Run the credit spreads scanner"""
        logger.info("="*60)
        logger.info("Starting Credit Spreads Scanner")
        logger.info("="*60)
        
        start_time = datetime.utcnow()
        results = []
        
        try:
            async with CreditSpreadDetector() as detector:
                async for session in get_async_session():
                    # Get tickers with weekly options
                    weekly_tickers = await self.get_weekly_tickers(session)
                    logger.info(f"Found {len(weekly_tickers)} tickers with weekly options")
                    
                    if not weekly_tickers:
                        logger.warning("No tickers with weekly options found")
                        return {
                            'success': True,
                            'tickers_processed': 0,
                            'spreads_found': 0,
                            'message': 'No tickers with weekly options'
                        }
                    
                    # Analyze each ticker for credit spreads
                    for ticker in weekly_tickers:
                        result = await self.analyze_ticker_for_spreads(ticker, detector)
                        if result:
                            results.append(result)
                            if result.get('has_spread'):
                                self.spreads_found += 1
                        self.processed_count += 1
                        
                        # Log progress every 10 tickers
                        if self.processed_count % 10 == 0:
                            logger.info(f"Progress: {self.processed_count}/{len(weekly_tickers)} processed, {self.spreads_found} spreads found")
                    
                    # Update database with results
                    await self.update_database_results(session, results)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Build summary
            summary = {
                'success': True,
                'tickers_processed': self.processed_count,
                'spreads_found': self.spreads_found,
                'failed_symbols': self.failed_symbols,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Log summary
            logger.info("="*60)
            logger.info("Credit Spreads Scanner Completed")
            logger.info(f"Processed: {self.processed_count} tickers")
            logger.info(f"Spreads found: {self.spreads_found}")
            logger.info(f"Failed: {len(self.failed_symbols)}")
            logger.info(f"Time: {execution_time:.2f} seconds")
            logger.info("="*60)
            
            return summary
            
        except Exception as e:
            logger.error(f"Scanner failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tickers_processed': self.processed_count,
                'spreads_found': self.spreads_found
            }


async def scan_credit_spreads():
    """Main entry point for credit spreads scanning"""
    scanner = CreditSpreadsScanner()
    return await scanner.run()