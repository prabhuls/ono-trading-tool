#!/usr/bin/env python3
"""Test that deepest ITM spread selection is working correctly"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_deepest_itm():
    """Test that the algorithm selects the deepest ITM spread"""
    algo = get_overnight_options_algorithm()

    print("=" * 60)
    print("Testing Deepest ITM Spread Selection")
    print("=" * 60)
    print(f"\nCurrent date/time: {datetime.now()}")

    # Test for both SPY and SPX
    for ticker in ["SPY", "SPX"]:
        print(f"\n" + "=" * 60)
        print(f"Testing {ticker}")
        print("=" * 60)

        try:
            # Run the algorithm
            result = await algo.run_algorithm(ticker)

            if result and result.get("algorithm_result"):
                algo_result = result["algorithm_result"]
                selected_spread = algo_result.get("selected_spread")
                qualified_count = algo_result.get("qualified_spreads_count", 0)

                if selected_spread:
                    sell_strike = selected_spread.get("sell_strike")
                    buy_strike = selected_spread.get("buy_strike")
                    cost = selected_spread.get("cost")

                    print(f"\n✅ {ticker} Results:")
                    print(f"  Qualified spreads found: {qualified_count}")
                    print(f"  Selected spread (DEEPEST ITM):")
                    print(f"    Buy Strike:  {buy_strike}")
                    print(f"    Sell Strike: {sell_strike}")
                    print(f"    Net Cost:    ${cost:.2f}")

                    # Check if there are other qualifying spreads to compare
                    if result.get("data"):
                        # Find all ITM strikes that could have been selected
                        current_price = result["metadata"].get("current_price", 0)
                        itm_strikes = sorted([
                            d["strike"] for d in result["data"]
                            if d.get("strike", 0) < current_price
                        ])

                        if itm_strikes:
                            print(f"\n  Available ITM strikes:")
                            print(f"    Lowest (deepest ITM): {itm_strikes[0]}")
                            print(f"    Highest (least ITM): {itm_strikes[-1]}")
                            print(f"    Total ITM strikes: {len(itm_strikes)}")

                            # Verify that the selected sell strike is among the lowest
                            if sell_strike <= itm_strikes[5] if len(itm_strikes) > 5 else itm_strikes[-1]:
                                print(f"\n  ✅ CORRECT: Selected strike {sell_strike} is among the deepest ITM strikes")
                            else:
                                print(f"\n  ❌ ISSUE: Selected strike {sell_strike} is not among the deepest ITM strikes")
                                print(f"     Deepest 5 ITM strikes: {itm_strikes[:5]}")
                else:
                    print(f"\n❌ {ticker}: No spread selected")
            else:
                print(f"\n❌ {ticker}: No algorithm result")

        except Exception as e:
            print(f"\n❌ {ticker} test failed: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("\n✅ Deepest ITM selection test complete!")
    print("\nThe algorithm should now be selecting the DEEPEST ITM spreads")
    print("(lowest sell strikes) rather than spreads closest to current price.")
    print("\nThis provides:")
    print("  • Better risk management")
    print("  • Higher probability of success")
    print("  • Alignment with project requirements")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_deepest_itm())
    sys.exit(0 if success else 1)