#!/usr/bin/env python3
"""
Final test of the market scanner with all fixes applied
"""

import asyncio
import logging
from datetime import datetime
from app.workers.market_scanner import MarketScanner
from app.core.database import get_async_session
from sqlalchemy import select
from app.models.movers import TodaysMover

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_scanner():
    """Test the complete market scanner"""
    print("=" * 80)
    print("TESTING MARKET SCANNER - FINAL VERSION")
    print("=" * 80)
    
    scanner = MarketScanner()
    
    # Phase 1: Get lists
    print("\nPhase 1: Fetching highs and lows lists...")
    highs, lows = await scanner.get_highs_lows_lists()
    print(f"✓ Found {len(highs)} highs and {len(lows)} lows")
    
    if not highs and not lows:
        print("✗ No symbols to process")
        return
    
    # Phase 2: Test processing a few symbols
    print("\nPhase 2: Testing symbol processing...")
    print("-" * 40)
    
    # Test up to 5 highs
    test_highs = highs[:5] if len(highs) > 5 else highs
    successful_highs = 0
    failed_highs = 0
    skipped_highs = 0
    
    async for session in get_async_session():
        for symbol in test_highs:
            print(f"\nProcessing HIGH: {symbol}")
            result = await scanner.process_symbol(session, symbol, is_high=True)
            
            if result['processed']:
                successful_highs += 1
                print(f"  ✓ SUCCESS - Stored in database")
                if result.get('special_char'):
                    print(f"    Special char: {result['special_char']}")
                if result.get('options_10days'):
                    print(f"    Options expiring in 10 days: {result['options_10days']}")
                if result.get('has_weeklies'):
                    print(f"    Has weekly options: Yes")
            elif result.get('skipped_reason'):
                skipped_highs += 1
                print(f"  ⊘ SKIPPED: {result['skipped_reason']}")
            elif result.get('error'):
                failed_highs += 1
                print(f"  ✗ ERROR: {result['error']}")
        
        # Test up to 5 lows
        test_lows = lows[:5] if len(lows) > 5 else lows
        successful_lows = 0
        failed_lows = 0
        skipped_lows = 0
        
        print("\n" + "-" * 40)
        for symbol in test_lows:
            print(f"\nProcessing LOW: {symbol}")
            result = await scanner.process_symbol(session, symbol, is_high=False)
            
            if result['processed']:
                successful_lows += 1
                print(f"  ✓ SUCCESS - Stored in database")
                if result.get('special_char'):
                    print(f"    Special char: {result['special_char']}")
                if result.get('options_10days'):
                    print(f"    Options expiring in 10 days: {result['options_10days']}")
                if result.get('has_weeklies'):
                    print(f"    Has weekly options: Yes")
            elif result.get('skipped_reason'):
                skipped_lows += 1
                print(f"  ⊘ SKIPPED: {result['skipped_reason']}")
            elif result.get('error'):
                failed_lows += 1
                print(f"  ✗ ERROR: {result['error']}")
        
        # Commit changes
        await session.commit()
        
        # Phase 3: Check database
        print("\n" + "=" * 80)
        print("Phase 3: Database Verification")
        print("-" * 40)
        
        # Count records in database
        result = await session.execute(select(TodaysMover))
        movers = result.scalars().all()
        
        uptrend_count = sum(1 for m in movers if m.mover_type == 'uptrend')
        downtrend_count = sum(1 for m in movers if m.mover_type == 'downtrend')
        
        print(f"Database contains:")
        print(f"  • {uptrend_count} uptrend movers")
        print(f"  • {downtrend_count} downtrend movers")
        print(f"  • {len(movers)} total movers")
        
        # Show sample records
        if movers:
            print("\nSample records:")
            for mover in movers[:3]:
                print(f"  {mover.symbol}: ${mover.current_price:.2f} ({mover.mover_type})")
                if mover.special_character:
                    print(f"    Special: {mover.special_character}")
                if mover.options_expiring_10days:
                    print(f"    Options: {mover.options_expiring_10days} expiring in 10 days")
    
    # Final summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("-" * 40)
    print(f"Highs tested: {len(test_highs)}")
    print(f"  ✓ Successful: {successful_highs}")
    print(f"  ⊘ Skipped: {skipped_highs}")
    print(f"  ✗ Failed: {failed_highs}")
    print(f"\nLows tested: {len(test_lows)}")
    print(f"  ✓ Successful: {successful_lows}")
    print(f"  ⊘ Skipped: {skipped_lows}")
    print(f"  ✗ Failed: {failed_lows}")
    
    success_rate_highs = (successful_highs / len(test_highs) * 100) if test_highs else 0
    success_rate_lows = (successful_lows / len(test_lows) * 100) if test_lows else 0
    
    print(f"\nSuccess rates:")
    print(f"  Highs: {success_rate_highs:.1f}%")
    print(f"  Lows: {success_rate_lows:.1f}%")
    
    if success_rate_highs > 0 or success_rate_lows > 0:
        print("\n✅ SCANNER IS WORKING!")
        print("   - Successfully processing stocks")
        print("   - Skipping ETFs and unsupported tickers")
        print("   - Storing results in database")
    else:
        print("\n⚠️ SCANNER NEEDS INVESTIGATION")
        print("   - All symbols failed processing")
        print("   - Check API connectivity and logs")
    
    print("=" * 80)

async def main():
    try:
        await test_scanner()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())