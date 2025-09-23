#!/usr/bin/env python3
"""Test script to verify cache TTL implementation"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service, TheTradeListService


async def test_cache_ttl():
    """Test the cache TTL settings"""
    service = get_thetradelist_service()

    print("=" * 60)
    print("Testing Cache TTL Configuration")
    print("=" * 60)

    # Verify cache constants are set correctly
    print(f"\n📊 Cache TTL Settings:")
    print(f"  Static Data TTL:  {TheTradeListService.CACHE_TTL_STATIC} seconds ({TheTradeListService.CACHE_TTL_STATIC / 3600:.1f} hours)")
    print(f"  Dynamic Data TTL: {TheTradeListService.CACHE_TTL_DYNAMIC} seconds")

    # Verify the values match requirements
    expected_static = 25200  # 7 hours
    expected_dynamic = 5     # 5 seconds

    print(f"\n✅ Verification:")

    if TheTradeListService.CACHE_TTL_STATIC == expected_static:
        print(f"  ✓ Static TTL correct: {expected_static} seconds (7 hours)")
    else:
        print(f"  ✗ Static TTL incorrect: Expected {expected_static}, got {TheTradeListService.CACHE_TTL_STATIC}")

    if TheTradeListService.CACHE_TTL_DYNAMIC == expected_dynamic:
        print(f"  ✓ Dynamic TTL correct: {expected_dynamic} seconds")
    else:
        print(f"  ✗ Dynamic TTL incorrect: Expected {expected_dynamic}, got {TheTradeListService.CACHE_TTL_DYNAMIC}")

    # Test examples of what data uses which cache
    print(f"\n📋 Cache Usage Examples:")
    print(f"\nStatic Data (7-hour cache):")
    print(f"  • Option contract details (strike, expiration, type)")
    print(f"  • Available expiration dates")
    print(f"  • Strike price listings")
    print(f"  • Contract metadata")

    print(f"\nDynamic Data (5-second cache):")
    print(f"  • Bid/ask prices")
    print(f"  • Last trade prices")
    print(f"  • Volume and open interest")
    print(f"  • Stock prices (SPY, SPX)")
    print(f"  • Implied volatility")

    # Test a real endpoint to ensure caching works
    print(f"\n🔄 Testing Price Endpoint (5-second cache):")
    try:
        # First call - will fetch from API
        print("  Fetching SPY price (first call)...")
        price1 = await service.get_stock_price("SPY")
        print(f"  SPY Price: ${price1.get('price', 0):.2f}")

        # Second call - should be from cache
        print("  Fetching SPY price (second call - from cache)...")
        price2 = await service.get_stock_price("SPY")
        print(f"  SPY Price: ${price2.get('price', 0):.2f}")

        # Verify they match (cached result)
        if price1.get('price') == price2.get('price'):
            print("  ✓ Cache working correctly - same price returned")
        else:
            print("  ✗ Cache may not be working - prices differ")

    except Exception as e:
        print(f"  ⚠ Could not test price endpoint: {str(e)}")

    print(f"\n✅ Cache TTL configuration test complete!")

    # Summary
    all_correct = (
        TheTradeListService.CACHE_TTL_STATIC == expected_static and
        TheTradeListService.CACHE_TTL_DYNAMIC == expected_dynamic
    )

    if all_correct:
        print("\n🎉 All cache TTL settings are configured correctly!")
        print("  • Static data cached for 7 hours")
        print("  • Dynamic data cached for 5 seconds")
        return True
    else:
        print("\n❌ Cache TTL configuration needs adjustment")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_cache_ttl())
    sys.exit(0 if success else 1)