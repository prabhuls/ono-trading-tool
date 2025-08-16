#!/usr/bin/env python3
"""
Run Market Scanner Worker
Railway CRON job runner for scanning market and updating criteria
Schedule: Every 30 minutes during market hours (9:30 AM - 4:00 PM EST)
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.workers.market_scanner import scan_market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def is_market_hours():
    """Check if current time is during market hours"""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check market hours (9:30 AM - 4:00 PM EST)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close


async def main():
    """Main function to run market scanner"""
    logger.info("=" * 60)
    logger.info("Starting Market Scanner Worker")
    logger.info("=" * 60)
    
    # Check if market hours (optional - Railway CRON can handle scheduling)
    # Commented out to allow running outside market hours for testing/manual runs
    # if not is_market_hours():
    #     logger.info("Outside market hours - skipping scan")
    #     logger.info("Market hours: 9:30 AM - 4:00 PM EST, Monday-Friday")
    #     sys.exit(0)
    
    try:
        # Run market scanner
        results = await scan_market()
        
        # Log results
        logger.info("=" * 60)
        logger.info("Market Scan Completed Successfully")
        logger.info(f"Total processed: {results.get('total_processed', 0)}")
        logger.info(f"Criteria updates: {results.get('criteria_updates', 0)}")
        logger.info(f"Movers found: {results.get('movers_found', 0)}")
        logger.info(f"Main list updated: {results.get('main_list_count', 0)}")
        logger.info(f"Errors encountered: {len(results.get('errors', []))}")
        logger.info(f"Execution time: {results.get('execution_time', 0):.2f} seconds")
        
        if results.get('errors'):
            logger.warning(f"First 5 errors:")
            for error in results['errors'][:5]:
                logger.warning(f"  {error['symbol']}: {error['error']}")
            if len(results['errors']) > 5:
                logger.warning(f"... and {len(results['errors']) - 5} more")
        
        logger.info("=" * 60)
        
        # Exit successfully
        sys.exit(0)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Market Scanner failed: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())