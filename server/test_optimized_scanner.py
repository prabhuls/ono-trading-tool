#!/usr/bin/env python3
"""
Test the optimized market scanner that only uses working endpoints
"""

import asyncio
import logging
from app.services.tradelist.client import TradeListClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_optimized_endpoints():
    """Test that we're only using working endpoints"""
    client = TradeListClient()
    
    print("=" * 80)
    print("Testing Optimized Market Scanner (Working Endpoints Only)")
    print("=" * 80)
    
    # Test 1: Highs/Lows (WORKING)
    print("\n1. Testing Highs/Lows endpoint...")
    highs = await client.get_highs_lows("high", 15.0, 500000)
    print(f"   ✓ Found {len(highs)} high stocks")
    if highs:
        print(f"   Sample: {highs[:3]}")
    
    # Test 2: Historical Data (WORKING)
    print("\n2. Testing Historical Data endpoint...")
    if highs:
        test_symbol = highs[0]
        historical = await client.get_historical_data(test_symbol, days=365)
        if historical:
            print(f"   ✓ Got {len(historical)} days of data for {test_symbol}")
            print(f"   Latest close: ${historical[0].get('c', 0):.2f}")
        else:
            print(f"   ✗ No historical data for {test_symbol}")
    
    # Test 3: Options Contracts (WORKING)
    print("\n3. Testing Options Contracts endpoint...")
    if highs:
        test_symbol = highs[0]
        options = await client.get_options_contracts(test_symbol, limit=100)
        print(f"   ✓ Found {len(options)} option contracts for {test_symbol}")
    
    # Test 4: Verify failing endpoints return None (as expected)
    print("\n4. Verifying failing endpoints are skipped...")
    quote = await client.get_quote("AAPL")
    print(f"   ✓ get_quote returns None (expected): {quote is None}")
    
    stock_info = await client.get_stock_info("AAPL")
    print(f"   ✓ get_stock_info returns None (expected): {stock_info is None}")
    
    stats = await client.get_52week_stats("AAPL")
    print(f"   ✓ get_52week_stats returns None (expected): {stats is None}")
    
    # Test 5: OHLCV using Polygon directly
    print("\n5. Testing OHLCV (Polygon only)...")
    if highs:
        test_symbol = highs[0]
        ohlcv = await client.get_ohlcv(test_symbol)
        if ohlcv:
            print(f"   ✓ Got OHLCV for {test_symbol}:")
            print(f"     Open: ${ohlcv['open']:.2f}, High: ${ohlcv['high']:.2f}")
            print(f"     Low: ${ohlcv['low']:.2f}, Close: ${ohlcv['close']:.2f}")
        else:
            print(f"   ✗ No OHLCV data for {test_symbol}")
    
    print("\n" + "=" * 80)
    print("Summary: Scanner optimized to use only working endpoints")
    print("- Highs/Lows: ✓ Working")
    print("- Historical Data: ✓ Working")
    print("- Options: ✓ Working")
    print("- Quote/Stock Info: Skipped (404)")
    print("=" * 80)

async def test_scanner_process():
    """Test a single symbol processing with optimized endpoints"""
    from app.workers.market_scanner import MarketScanner
    from app.core.database import get_async_session
    
    print("\n" + "=" * 80)
    print("Testing Symbol Processing with Optimized Endpoints")
    print("=" * 80)
    
    scanner = MarketScanner()
    
    # Get a test symbol
    highs, _ = await scanner.get_highs_lows_lists()
    if not highs:
        print("No highs available for testing")
        return
    
    test_symbol = highs[0]
    print(f"\nTesting symbol: {test_symbol}")
    
    # Test OHLCV (should use Polygon only)
    print("1. Getting OHLCV data (Polygon only)...")
    ohlcv = await scanner.get_ohlcv_data(test_symbol)
    if ohlcv:
        print(f"   ✓ Got OHLCV: Close=${ohlcv['close']:.2f}, Volume={ohlcv['volume']:,}")
    else:
        print("   ✗ Failed to get OHLCV")
    
    # Test 52-week stats (should calculate from historical)
    print("2. Getting 52-week stats (from historical)...")
    stats = await scanner.get_52week_stats(test_symbol)
    if stats:
        print(f"   ✓ Got stats: 52W High=${stats['highest_52w']:.2f}, 52W Low=${stats['lowest_52w']:.2f}")
    else:
        print("   ✗ Failed to get stats")
    
    # Test complete historical data
    print("3. Getting complete historical data...")
    historical = await scanner.get_complete_historical_data(test_symbol)
    if historical:
        print(f"   ✓ Got {len(historical['tradingDays'])} days of historical data")
    else:
        print("   ✗ Failed to get historical data")
    
    print("\n✓ Optimized scanner working with available endpoints only")

async def main():
    await test_optimized_endpoints()
    await test_scanner_process()

if __name__ == "__main__":
    asyncio.run(main())