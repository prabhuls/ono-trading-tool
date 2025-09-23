#!/usr/bin/env python3
"""Test that all components show consistent expiration dates"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.market_status_enhanced_service import get_market_status_enhanced_service
from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_expiration_consistency():
    """Test that all components show the same expiration date"""

    print("=" * 60)
    print("Testing Expiration Date Consistency Across All Components")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    try:
        # Get services
        market_service = get_market_status_enhanced_service()
        tradelist_service = get_thetradelist_service()
        algorithm = get_overnight_options_algorithm()

        print("\n📅 Fetching expiration dates from all sources...")

        # 1. Direct API call (source of truth)
        api_expiration = await tradelist_service.get_next_trading_day_expiration("SPY")
        print(f"\n1. TheTradeList API (direct):     {api_expiration}")

        # 2. Market Status sidebar
        sidebar_data = await market_service.get_sidebar_status_data()
        sidebar_expiration = sidebar_data.get("next_expiration")
        print(f"2. Market Status sidebar:          {sidebar_expiration}")

        # 3. Algorithm for SPY
        print("\n3. Running SPY algorithm...")
        spy_result = await algorithm.run_algorithm("SPY")
        spy_expiration = None
        if spy_result and spy_result.get("metadata"):
            spy_expiration = spy_result["metadata"].get("expiration_date")
        print(f"   SPY algorithm expiration:       {spy_expiration}")

        # 4. Algorithm for SPX
        print("\n4. Running SPX algorithm...")
        spx_result = await algorithm.run_algorithm("SPX")
        spx_expiration = None
        if spx_result and spx_result.get("metadata"):
            spx_expiration = spx_result["metadata"].get("expiration_date")
        print(f"   SPX algorithm expiration:       {spx_expiration}")

        # Verify consistency
        print("\n" + "=" * 60)
        print("Consistency Check:")
        print("=" * 60)

        all_match = True

        # Check Market Status
        if sidebar_expiration == api_expiration:
            print("✅ Market Status matches API")
        else:
            print(f"❌ Market Status mismatch: {sidebar_expiration} != {api_expiration}")
            all_match = False

        # Check SPY algorithm
        if spy_expiration == api_expiration:
            print("✅ SPY algorithm matches API")
        else:
            print(f"❌ SPY algorithm mismatch: {spy_expiration} != {api_expiration}")
            all_match = False

        # Check SPX algorithm
        if spx_expiration == api_expiration:
            print("✅ SPX algorithm matches API")
        else:
            print(f"❌ SPX algorithm mismatch: {spx_expiration} != {api_expiration}")
            all_match = False

        # Summary
        print("\n" + "=" * 60)
        if all_match:
            print("🎉 SUCCESS: All components show consistent expiration date!")
            print(f"📅 Unified expiration: {api_expiration}")
        else:
            print("⚠️  WARNING: Expiration dates are inconsistent across components")

        # Show selected spreads if available
        if spy_result and spy_result.get("algorithm_result", {}).get("selected_spread"):
            spread = spy_result["algorithm_result"]["selected_spread"]
            print(f"\n📊 SPY Selected Spread:")
            print(f"   Buy:  {spread['buy_strike']} | Sell: {spread['sell_strike']} | Cost: ${spread['cost']:.2f}")

        if spx_result and spx_result.get("algorithm_result", {}).get("selected_spread"):
            spread = spx_result["algorithm_result"]["selected_spread"]
            print(f"\n📊 SPX Selected Spread:")
            print(f"   Buy:  {spread['buy_strike']} | Sell: {spread['sell_strike']} | Cost: ${spread['cost']:.2f}")

        return all_match

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_expiration_consistency())
    sys.exit(0 if success else 1)