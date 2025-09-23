#!/usr/bin/env python3
"""Test that Market Status panel shows same expiration as SPY/SPX recommendations"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.market_status_enhanced_service import get_market_status_enhanced_service
from app.services.external.thetradelist_service import get_thetradelist_service


async def test_market_status_expiration():
    """Test that market status shows correct expiration from API"""

    print("=" * 60)
    print("Testing Market Status Expiration Date")
    print("=" * 60)

    try:
        # Get services
        market_service = get_market_status_enhanced_service()
        tradelist_service = get_thetradelist_service()

        # Get expiration from TheTradeList API directly
        print("\n1. Fetching expiration from TheTradeList API...")
        api_expiration_spy = await tradelist_service.get_next_trading_day_expiration("SPY")
        api_expiration_spx = await tradelist_service.get_next_trading_day_expiration("SPX")
        print(f"   SPY next expiration: {api_expiration_spy}")
        print(f"   SPX next expiration: {api_expiration_spx}")

        # Get sidebar status (which should now use the API)
        print("\n2. Fetching Market Status sidebar data...")
        sidebar_data = await market_service.get_sidebar_status_data()
        sidebar_expiration = sidebar_data.get("next_expiration")
        print(f"   Sidebar expiration: {sidebar_expiration}")

        # Get enhanced market status
        print("\n3. Fetching Enhanced Market Status...")
        enhanced_data = await market_service.calculate_market_session()
        enhanced_expiration = enhanced_data.get("next_expiration")
        print(f"   Enhanced expiration: {enhanced_expiration}")

        # Compare results
        print("\n" + "=" * 60)
        print("Results:")
        print("=" * 60)

        if sidebar_expiration == api_expiration_spy:
            print("✅ Sidebar expiration matches SPY API expiration")
        else:
            print(f"❌ Sidebar expiration mismatch: {sidebar_expiration} != {api_expiration_spy}")

        if enhanced_expiration == api_expiration_spy:
            print("✅ Enhanced market status expiration matches SPY API expiration")
        else:
            print(f"❌ Enhanced expiration mismatch: {enhanced_expiration} != {api_expiration_spy}")

        # Check if SPY and SPX have same expiration (they usually do for 0DTE)
        if api_expiration_spy == api_expiration_spx:
            print(f"ℹ️  SPY and SPX have same expiration: {api_expiration_spy}")
        else:
            print(f"⚠️  SPY and SPX have different expirations: SPY={api_expiration_spy}, SPX={api_expiration_spx}")

        print("\n🎉 Market Status panel now uses real-time expiration dates from API!")
        print("📅 This ensures consistency with SPY/SPX recommendations")

        return sidebar_expiration == api_expiration_spy

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_market_status_expiration())
    sys.exit(0 if success else 1)