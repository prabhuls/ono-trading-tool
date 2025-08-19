#!/usr/bin/env python3
"""
Run Daily Cleanup Worker
Railway CRON job runner for daily transfer and cleanup operations
Schedule: Daily at 5 PM ET (22:00 UTC)

Process:
1. Archive current Main Lists to 7-day tracker
2. Transfer Today's Movers → Main Lists
3. Clear Today's Movers table
4. Clean up archive records older than 7 days
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.workers.daily_cleanup import run_daily_cleanup

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
    """Main function to run daily cleanup"""
    logger.info("=" * 60)
    logger.info("Starting Daily Cleanup Process")
    logger.info("=" * 60)
    
    try:
        # Run daily cleanup
        results = await run_daily_cleanup()
        
        if results.get('success'):
            # Log success results
            logger.info("=" * 60)
            logger.info("Daily Cleanup Completed Successfully")
            logger.info(f"Records transferred: {results.get('transferred', 0)}")
            logger.info(f"New archive records: {results.get('archived_new', 0)}")
            logger.info(f"Updated archive records: {results.get('archived_updated', 0)}")
            logger.info(f"Expired records cleaned: {results.get('cleaned', 0)}")
            logger.info(f"Execution time: {results.get('execution_time', 0):.2f} seconds")
            logger.info("=" * 60)
            
            # Exit successfully
            sys.exit(0)
        else:
            # Log failure
            logger.error("=" * 60)
            logger.error("Daily Cleanup Failed")
            if 'message' in results:
                logger.error(f"Message: {results['message']}")
            if 'error' in results:
                logger.error(f"Error: {results['error']}")
            logger.error("=" * 60)
            
            # Exit with error code
            sys.exit(1)
            
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Daily Cleanup failed with exception: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        # Give async tasks time to cleanup
        import time
        time.sleep(0.5)