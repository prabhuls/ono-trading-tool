#!/usr/bin/env python3
"""Test script for new sp-prices endpoint integration"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service


async def test_sp_prices():
    """Test the new sp-prices endpoint"""
    service = get_thetradelist_service()

    try:
        # Test new sp-prices endpoint
        print("=" * 60)
        print("Testing new sp-prices endpoint...")
        print("=" * 60)

        sp_data = await service.get_sp_prices()

        print("\n📊 SP Prices Response:")
        for ticker in ["SPY", "SPX"]:
            if sp_data.get(ticker):
                data = sp_data[ticker]
                print(f"\n{ticker}:")
                print(f"  Price: ${data['price']:.2f}")
                print(f"  Net Change: {data['net_change']:.2f}")
                print(f"  Net Change %: {data['net_change_pct']:.2f}%")
                print(f"  Timestamp: {data['timestamp']}")

        # Test individual ticker calls (should use sp-prices internally)
        print("\n" + "=" * 60)
        print("Testing individual ticker calls (using sp-prices internally):")
        print("=" * 60)

        for ticker in ["SPY", "SPX"]:
            price_data = await service.get_stock_price(ticker)
            print(f"\n{ticker}:")
            print(f"  Price: ${price_data['price']:.2f}")
            print(f"  Change: {price_data['change']:.2f}")
            print(f"  Change %: {price_data['change_percent']:.2f}%")

        print("\n✅ All tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_sp_prices())
    sys.exit(0 if success else 1)