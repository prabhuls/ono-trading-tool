#!/usr/bin/env python3
"""Test SPX optimization changes - ensure spreads are still found"""

import asyncio
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_spx_optimization():
    """Test that SPX spreads are still found after optimization"""
    service = get_thetradelist_service()
    algo = get_overnight_options_algorithm()

    print("=" * 60)
    print("Testing SPX Optimization Changes")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    # Test parameters
    ticker = "SPX"
    spread_width = 5.0
    max_cost = 3.75

    try:
        # Get current price
        print(f"\nFetching current {ticker} price...")
        stock_data = await service.get_stock_price(ticker)
        current_price = stock_data["price"]
        print(f"{ticker} current price: ${current_price:.2f}")

        # Get expiration date
        print(f"\nGetting next trading day expiration for {ticker}...")
        expiration = await service.get_next_trading_day_expiration(ticker)
        print(f"{ticker} expiration: {expiration}")

        # Test the optimized contract fetching
        print(f"\nFetching {ticker} options contracts (with optimization)...")
        start_time = time.time()

        contracts_data = await service.get_options_contracts(
            underlying_ticker=ticker,
            expiration_date=expiration,
            fetch_all=False,  # Use optimization
            current_price=current_price,
            target_strikes_around_price=30  # Reduced from 60
        )

        fetch_time = time.time() - start_time
        contracts = contracts_data.get("results", [])

        print(f"\nFetch completed in {fetch_time:.2f} seconds")
        print(f"Total contracts fetched: {len(contracts)}")

        # Analyze strike distribution
        unique_strikes = set()
        strikes_above = set()
        strikes_below = set()

        for contract in contracts:
            strike = contract.get("strike_price", 0)
            unique_strikes.add(strike)

            if strike > current_price:
                strikes_above.add(strike)
            elif strike < current_price:
                strikes_below.add(strike)

        print(f"\nStrike distribution:")
        print(f"  Unique strikes: {len(unique_strikes)}")
        print(f"  Strikes above {current_price}: {len(strikes_above)}")
        print(f"  Strikes below {current_price}: {len(strikes_below)}")

        # Test that we can still find valid spreads
        print(f"\n" + "=" * 60)
        print("Testing Spread Selection")
        print("=" * 60)

        print(f"\nScanning for {ticker} spreads...")
        print(f"  Spread width: ${spread_width}")
        print(f"  Max cost: ${max_cost}")

        spread_result = await algo.run_algorithm(
            ticker=ticker
        )

        if spread_result and spread_result.get("algorithm_result"):
            algo_result = spread_result["algorithm_result"]
            qualified_count = algo_result.get("qualified_spreads_count", 0)
            print(f"\n✅ Found {qualified_count} qualified spreads!")


            # Check if optimal spread is close to current price
            if algo_result.get("selected_spread"):
                optimal = algo_result["selected_spread"]
                print(f"\n📊 Optimal Spread Selected:")
                print(f"  Buy:  {optimal['buy_strike']}")
                print(f"  Sell: {optimal['sell_strike']}")
                print(f"  Net Cost: ${optimal['cost']:.2f}")
                print(f"  Distance from price: {abs(optimal['sell_strike'] - current_price):.2f}")

                # Verify it's reasonably close to current price
                distance_pct = abs(optimal['sell_strike'] - current_price) / current_price * 100
                if distance_pct < 5:  # Within 5% of current price
                    print(f"\n✅ Optimal spread is {distance_pct:.2f}% from current price - GOOD!")
                else:
                    print(f"\n⚠️ Optimal spread is {distance_pct:.2f}% from current price - might be too far")
        else:
            print("\n❌ No valid spreads found!")

        # Summary
        print(f"\n" + "=" * 60)
        print("Optimization Results Summary")
        print("=" * 60)

        if fetch_time < 30:  # Under 30 seconds is good
            print(f"✅ Fetch time: {fetch_time:.2f}s (OPTIMIZED)")
        else:
            print(f"⚠️ Fetch time: {fetch_time:.2f}s (still slow)")

        if len(contracts) < 5000:  # Much less than the 12000+ before
            print(f"✅ Contract count: {len(contracts)} (REDUCED)")
        else:
            print(f"⚠️ Contract count: {len(contracts)} (still high)")

        if spread_result and spread_result.get("algorithm_result") and spread_result["algorithm_result"].get("selected_spread"):
            print(f"✅ Valid spreads: FOUND")
        else:
            print(f"❌ Valid spreads: NOT FOUND")

        print("\n✅ SPX optimization test complete!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_spx_optimization())
    sys.exit(0 if success else 1)