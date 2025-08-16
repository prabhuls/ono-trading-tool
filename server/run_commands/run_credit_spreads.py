#!/usr/bin/env python3
"""
Run Credit Spreads Batch Scanner
Railway CRON job runner for analyzing credit spread opportunities
Schedule: Every 4 hours
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.workers.credit_spreads_scanner import scan_credit_spreads

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
    """Main function to run credit spreads batch scanner"""
    logger.info("=" * 60)
    logger.info("Starting Credit Spreads Batch Scanner")
    logger.info("=" * 60)
    
    try:
        # Run credit spreads scanner
        results = await scan_credit_spreads()
        
        # Log results
        logger.info("=" * 60)
        logger.info("Credit Spreads Scan Completed Successfully")
        logger.info(f"Total processed: {results.get('total_processed', 0)}")
        logger.info(f"Total opportunities: {results.get('total_opportunities', 0)}")
        logger.info(f"Total failed: {results.get('total_failed', 0)}")
        
        # Strategy breakdown
        summary = results.get('summary', {})
        if summary:
            logger.info("Strategy breakdown:")
            logger.info(f"  Conservative: {summary.get('conservative_opportunities', 0)}")
            logger.info(f"  Balanced: {summary.get('balanced_opportunities', 0)}")
            logger.info(f"  Aggressive: {summary.get('aggressive_opportunities', 0)}")
        
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
        logger.error(f"Credit Spreads Scanner failed: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())