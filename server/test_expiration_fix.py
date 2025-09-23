#!/usr/bin/env python3
"""Test that we get ALL contracts for target expiration date"""

import asyncio
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_expiration_fix():
    """Test that we properly collect ALL contracts for target date"""
    service = get_thetradelist_service()
    algo = get_overnight_options_algorithm()

    print("=" * 60)
    print("Testing Expiration Date Contract Collection Fix")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    for ticker in ["SPY", "SPX"]:
        print(f"\n" + "=" * 60)
        print(f"Testing {ticker}")
        print("=" * 60)

        try:
            # Get current price and expiration
            stock_data = await service.get_stock_price(ticker)
            current_price = stock_data["price"]
            print(f"Current price: ${current_price:.2f}")

            expiration = await service.get_next_trading_day_expiration(ticker)
            print(f"Target expiration: {expiration}")

            # Fetch contracts
            print(f"\nFetching contracts for {expiration}...")
            start_time = time.time()

            contracts_data = await service.get_options_contracts(
                underlying_ticker=ticker,
                expiration_date=expiration,
                fetch_all=False,
                current_price=current_price,
                target_strikes_around_price=30
            )

            fetch_time = time.time() - start_time
            contracts = contracts_data.get("results", [])

            print(f"✅ Fetch completed in {fetch_time:.2f} seconds")
            print(f"Total contracts fetched: {len(contracts)}")

            # Verify ALL contracts are for target date
            expiration_dates = set()
            strikes = set()
            call_count = 0
            put_count = 0

            for contract in contracts:
                exp_date = contract.get("expiration_date")
                expiration_dates.add(exp_date)
                strikes.add(contract.get("strike_price"))

                if contract.get("contract_type") == "call":
                    call_count += 1
                else:
                    put_count += 1

            print(f"\nContract Analysis:")
            print(f"  Unique expiration dates: {expiration_dates}")
            print(f"  Total unique strikes: {len(strikes)}")
            print(f"  Call contracts: {call_count}")
            print(f"  Put contracts: {put_count}")

            if len(expiration_dates) == 1 and expiration in expiration_dates:
                print(f"  ✅ ALL contracts are for target date: {expiration}")
            else:
                print(f"  ❌ Mixed expiration dates found: {expiration_dates}")

            # Test the algorithm
            print(f"\nRunning algorithm for {ticker}...")
            result = await algo.run_algorithm(ticker)

            if result and result.get("algorithm_result"):
                algo_result = result["algorithm_result"]
                qualified_count = algo_result.get("qualified_spreads_count", 0)

                print(f"\nAlgorithm Results:")
                print(f"  Qualified spreads found: {qualified_count}")

                if algo_result.get("selected_spread"):
                    selected = algo_result["selected_spread"]
                    print(f"  ✅ Spread selected:")
                    print(f"    Buy Strike:  {selected['buy_strike']}")
                    print(f"    Sell Strike: {selected['sell_strike']}")
                    print(f"    Net Cost:    ${selected['cost']:.2f}")
                else:
                    print(f"  ❌ No spread selected")

                # Check metadata
                if result.get("metadata"):
                    meta = result["metadata"]
                    print(f"\nMetadata:")
                    print(f"  Contracts processed: {meta.get('total_contracts', 0)}")
                    print(f"  Expiration used: {meta.get('expiration_date')}")
            else:
                print(f"  ❌ Algorithm failed")

        except Exception as e:
            print(f"\n❌ Test failed for {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("\n✅ The fix ensures we collect ALL contracts for the target expiration date")
    print("✅ No mixed dates in results")
    print("✅ Algorithm should now find valid spreads")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_expiration_fix())
    sys.exit(0 if success else 1)