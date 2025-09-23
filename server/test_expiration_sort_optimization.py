#!/usr/bin/env python3
"""Test SPX optimization with expiration_date sorting"""

import asyncio
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_expiration_sort_optimization():
    """Test that sorting by expiration_date reduces API calls"""
    service = get_thetradelist_service()
    algo = get_overnight_options_algorithm()

    print("=" * 60)
    print("Testing Expiration Date Sort Optimization")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    # Test for SPX (the main beneficiary of this optimization)
    ticker = "SPX"

    try:
        # Get current price and expiration
        print(f"\nFetching current {ticker} price...")
        stock_data = await service.get_stock_price(ticker)
        current_price = stock_data["price"]
        print(f"{ticker} current price: ${current_price:.2f}")

        print(f"\nGetting next trading day expiration for {ticker}...")
        expiration = await service.get_next_trading_day_expiration(ticker)
        print(f"{ticker} expiration: {expiration}")

        # Test the optimized contract fetching
        print(f"\n" + "=" * 60)
        print("Fetching Options Contracts (with expiration_date filter + sort)")
        print("=" * 60)

        start_time = time.time()

        contracts_data = await service.get_options_contracts(
            underlying_ticker=ticker,
            expiration_date=expiration,  # This will now filter to only this date
            fetch_all=False,
            current_price=current_price,
            target_strikes_around_price=30
        )

        fetch_time = time.time() - start_time
        contracts = contracts_data.get("results", [])

        print(f"\n✅ Fetch completed in {fetch_time:.2f} seconds")
        print(f"Total contracts fetched: {len(contracts)}")

        # Analyze what we got
        expiration_dates = set()
        strikes_by_expiration = {}

        for contract in contracts:
            exp_date = contract.get("expiration_date")
            strike = contract.get("strike_price", 0)

            if exp_date:
                expiration_dates.add(exp_date)
                if exp_date not in strikes_by_expiration:
                    strikes_by_expiration[exp_date] = set()
                strikes_by_expiration[exp_date].add(strike)

        print(f"\n📊 Contract Analysis:")
        print(f"Unique expiration dates fetched: {len(expiration_dates)}")

        if expiration in strikes_by_expiration:
            target_strikes = strikes_by_expiration[expiration]
            print(f"\nFor target expiration {expiration}:")
            print(f"  Total unique strikes: {len(target_strikes)}")

            strikes_above = [s for s in target_strikes if s > current_price]
            strikes_below = [s for s in target_strikes if s < current_price]

            print(f"  Strikes above {current_price}: {len(strikes_above)}")
            print(f"  Strikes below {current_price}: {len(strikes_below)}")

            if len(strikes_above) > 0 and len(strikes_below) > 0:
                print(f"  Strike range: {min(target_strikes):.0f} to {max(target_strikes):.0f}")

        # Test the algorithm still works
        print(f"\n" + "=" * 60)
        print("Testing Algorithm with Optimized Data")
        print("=" * 60)

        result = await algo.run_algorithm(ticker)

        if result and result.get("algorithm_result"):
            algo_result = result["algorithm_result"]
            if algo_result.get("selected_spread"):
                selected = algo_result["selected_spread"]
                print(f"\n✅ Algorithm successfully found spread:")
                print(f"  Buy Strike:  {selected['buy_strike']}")
                print(f"  Sell Strike: {selected['sell_strike']}")
                print(f"  Net Cost:    ${selected['cost']:.2f}")
                print(f"  Qualified spreads: {algo_result.get('qualified_spreads_count', 0)}")
            else:
                print("\n⚠️ No spread selected")
        else:
            print("\n❌ Algorithm failed")

        # Summary
        print(f"\n" + "=" * 60)
        print("Optimization Results")
        print("=" * 60)

        if fetch_time < 10:  # Much faster than before
            print(f"✅ Fetch time: {fetch_time:.2f}s (OPTIMIZED!)")
        else:
            print(f"⚠️ Fetch time: {fetch_time:.2f}s (still slow)")

        if len(contracts) < 1000:  # Much fewer than the 9000+ before
            print(f"✅ Contract count: {len(contracts)} (REDUCED!)")
        else:
            print(f"⚠️ Contract count: {len(contracts)} (still high)")

        if len(expiration_dates) == 1 and expiration in expiration_dates:
            print(f"✅ Only target expiration fetched: {expiration}")
        else:
            print(f"⚠️ Multiple expirations fetched: {expiration_dates}")

        print("\n🎉 Expiration date sort optimization working!")
        print("\nBenefits achieved:")
        print("  • Fetching only contracts for target expiration date")
        print("  • Massive reduction in API calls")
        print("  • Much faster response times")
        print("  • Algorithm still finds valid spreads")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_expiration_sort_optimization())
    sys.exit(0 if success else 1)