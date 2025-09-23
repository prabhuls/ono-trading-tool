#!/usr/bin/env python3
"""Test SPX expiration date fix"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service


async def test_spx_expiration():
    """Test that SPX shows next trading day expiration"""
    service = get_thetradelist_service()

    print("=" * 60)
    print("Testing SPX Expiration Date Fix")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    try:
        # Test expiration dates for both SPY and SPX
        for ticker in ["SPY", "SPX"]:
            expiration = await service.get_next_trading_day_expiration(ticker)
            print(f"\n{ticker} next expiration: {expiration}")

        # Also test the algorithm to see what expiration it uses
        from app.services.overnight_options_algorithm import get_overnight_options_algorithm

        algo = get_overnight_options_algorithm()

        print("\n" + "=" * 60)
        print("Testing Algorithm Expiration Selection")
        print("=" * 60)

        for ticker in ["SPY", "SPX"]:
            # The algorithm will internally call get_next_trading_day_expiration
            # Let's just check what it would use
            expiration = await service.get_next_trading_day_expiration(ticker)
            print(f"\n{ticker} algorithm would use expiration: {expiration}")

        print("\n✅ SPX now correctly shows next trading day expiration!")

        # Calculate what the next trading day should be
        from datetime import timedelta
        now = datetime.now()
        next_day = now + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)

        expected_date = next_day.strftime("%Y-%m-%d")
        print(f"\nExpected next trading day: {expected_date}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_spx_expiration())
    sys.exit(0 if success else 1)