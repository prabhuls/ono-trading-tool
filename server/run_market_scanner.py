#!/usr/bin/env python3
"""
Run the market scanner
"""

import asyncio
import sys
import logging
from app.workers.market_scanner import scan_market

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main entry point"""
    print("=" * 60)
    print("MARKET SCANNER - STARTING")
    print("=" * 60)
    
    try:
        results = await scan_market()
        
        print("\n" + "=" * 60)
        print("MARKET SCANNER - COMPLETED")
        print("=" * 60)
        print(f"Highs processed: {results.get('highs_processed', 0)}")
        print(f"Lows processed: {results.get('lows_processed', 0)}")
        print(f"Highs skipped (variability): {results.get('highs_skipped_variability', 0)}")
        print(f"Lows skipped (variability): {results.get('lows_skipped_variability', 0)}")
        print(f"Total in database: {results.get('total_in_database', 0)}")
        print(f"Execution time: {results.get('execution_time', 0):.2f} seconds")
        print("=" * 60)
        
        return 0
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        logging.error(f"Scanner failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)