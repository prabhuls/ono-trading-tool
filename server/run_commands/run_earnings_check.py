#!/usr/bin/env python3
"""
Run Earnings Check Worker
Railway CRON job runner for checking and updating earnings dates
Schedule: Daily at 2 AM UTC
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.workers.earnings_checker import check_earnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run earnings check"""
    logger.info("=" * 60)
    logger.info("Starting Earnings Check Worker")
    logger.info("=" * 60)
    
    try:
        # Run earnings check
        results = await check_earnings()
        
        # Log results
        logger.info("=" * 60)
        logger.info("Earnings Check Completed Successfully")
        logger.info(f"Total processed: {results.get('total_processed', 0)}")
        logger.info(f"Total updated: {results.get('total_updated', 0)}")
        logger.info(f"Total with upcoming earnings: {results.get('total_with_upcoming_earnings', 0)}")
        logger.info(f"Total failed: {results.get('total_failed', 0)}")
        logger.info(f"Execution time: {results.get('execution_time', 0):.2f} seconds")
        
        if results.get('failed_symbols'):
            logger.warning(f"Failed symbols: {', '.join(results['failed_symbols'][:10])}")
            if len(results['failed_symbols']) > 10:
                logger.warning(f"... and {len(results['failed_symbols']) - 10} more")
        
        logger.info("=" * 60)
        
        # Exit successfully
        sys.exit(0)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Earnings Check Worker failed: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())