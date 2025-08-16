#!/usr/bin/env python3
"""
Run the credit spreads scanner
Analyzes todays_movers with weekly options for credit spread opportunities
"""

import asyncio
import sys
import logging
from app.workers.credit_spreads_scanner import scan_credit_spreads

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main entry point"""
    print("=" * 60)
    print("CREDIT SPREADS SCANNER - STARTING")
    print("=" * 60)
    print("Scanning todays_movers for credit spread opportunities...")
    print("Target: Tickers with weekly options")
    print("Strategy: Trend-based (uptrend=puts, downtrend=calls)")
    print("-" * 60)
    
    try:
        results = await scan_credit_spreads()
        
        print("\n" + "=" * 60)
        print("CREDIT SPREADS SCANNER - COMPLETED")
        print("=" * 60)
        
        if results.get('success'):
            print(f"\n✓ Scanner completed successfully")
            print(f"  Tickers processed: {results.get('tickers_processed', 0)}")
            print(f"  Spreads found: {results.get('spreads_found', 0)}")
            
            if results.get('failed_symbols'):
                print(f"  Failed symbols: {', '.join(results['failed_symbols'])}")
            
            print(f"\nDatabase updated:")
            print(f"  • has_spreads=true for {results.get('spreads_found', 0)} tickers")
            print(f"  • has_spreads=false for all other tickers")
            
            print(f"\nExecution time: {results.get('execution_time', 0):.2f} seconds")
        else:
            print(f"\n✗ Scanner failed")
            print(f"  Error: {results.get('error', 'Unknown error')}")
            print(f"  Processed before failure: {results.get('tickers_processed', 0)}")
        
        print("=" * 60)
        
        return 0 if results.get('success') else 1
        
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        logging.error(f"Scanner failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)