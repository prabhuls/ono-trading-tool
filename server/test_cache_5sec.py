#!/usr/bin/env python3
"""Test that cache TTL is now 5 seconds for both static and dynamic data"""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service, TheTradeListService


async def test_cache_5sec():
    """Test that both cache TTLs are set to 5 seconds"""

    print("=" * 60)
    print("Testing Cache TTL Configuration (5 seconds)")
    print("=" * 60)

    # Verify cache constants are set correctly
    print(f"\n📊 Cache TTL Settings:")
    print(f"  Static Data TTL:  {TheTradeListService.CACHE_TTL_STATIC} seconds")
    print(f"  Dynamic Data TTL: {TheTradeListService.CACHE_TTL_DYNAMIC} seconds")

    # Verify both are 5 seconds
    expected_ttl = 5  # 5 seconds for both

    print(f"\n✅ Verification:")

    all_correct = True

    if TheTradeListService.CACHE_TTL_STATIC == expected_ttl:
        print(f"  ✓ Static TTL correct: {expected_ttl} seconds")
    else:
        print(f"  ✗ Static TTL incorrect: Expected {expected_ttl}, got {TheTradeListService.CACHE_TTL_STATIC}")
        all_correct = False

    if TheTradeListService.CACHE_TTL_DYNAMIC == expected_ttl:
        print(f"  ✓ Dynamic TTL correct: {expected_ttl} seconds")
    else:
        print(f"  ✗ Dynamic TTL incorrect: Expected {expected_ttl}, got {TheTradeListService.CACHE_TTL_DYNAMIC}")
        all_correct = False

    # Test actual cache behavior with stock price
    print(f"\n🔄 Testing Cache Refresh (5-second TTL):")

    try:
        service = get_thetradelist_service()

        # First call - will fetch from API
        print("\n1️⃣ First call (fetches from API):")
        start1 = time.time()
        price1 = await service.get_stock_price("SPY")
        time1 = time.time() - start1
        print(f"   SPY Price: ${price1['price']:.2f}")
        print(f"   Time taken: {time1:.2f}s")

        # Second call immediately - should be from cache (fast)
        print("\n2️⃣ Second call immediately (from cache):")
        start2 = time.time()
        price2 = await service.get_stock_price("SPY")
        time2 = time.time() - start2
        print(f"   SPY Price: ${price2['price']:.2f}")
        print(f"   Time taken: {time2:.2f}s")

        if time2 < time1 / 2:  # Cache should be much faster
            print(f"   ✓ Served from cache (fast response)")

        # Wait 3 seconds (still within 5-second cache)
        print("\n⏳ Waiting 3 seconds (within 5-second cache window)...")
        await asyncio.sleep(3)

        # Third call - should still be from cache
        print("\n3️⃣ Third call after 3 seconds (should still be cached):")
        start3 = time.time()
        price3 = await service.get_stock_price("SPY")
        time3 = time.time() - start3
        print(f"   SPY Price: ${price3['price']:.2f}")
        print(f"   Time taken: {time3:.2f}s")

        if price3['price'] == price2['price'] and time3 < time1 / 2:
            print(f"   ✓ Still served from cache")

        # Wait another 3 seconds (total 6 seconds - cache should expire)
        print("\n⏳ Waiting another 3 seconds (total 6 seconds - cache should expire)...")
        await asyncio.sleep(3)

        # Fourth call - cache should have expired, fetch new data
        print("\n4️⃣ Fourth call after 6 seconds total (cache should refresh):")
        start4 = time.time()
        price4 = await service.get_stock_price("SPY")
        time4 = time.time() - start4
        print(f"   SPY Price: ${price4['price']:.2f}")
        print(f"   Time taken: {time4:.2f}s")

        if time4 > time3:  # Should take longer than cached response
            print(f"   ✓ Cache refreshed (slower response indicates API call)")

    except Exception as e:
        print(f"\n⚠ Could not test cache behavior: {str(e)}")
        all_correct = False

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if all_correct:
        print("🎉 All cache TTL settings are configured correctly!")
        print("  • Both static and dynamic data cached for 5 seconds")
        print("\n⚠️  Note: This will significantly increase API calls")
        print("    (Previously static data was cached for 7 hours)")
    else:
        print("❌ Cache TTL configuration needs adjustment")

    return all_correct


if __name__ == "__main__":
    success = asyncio.run(test_cache_5sec())
    sys.exit(0 if success else 1)