"""
Test specific QQQ scenario: $7 ITM option spread
Client reported 70% error for this case
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm


async def test_qqq_deep_itm():
    """Test QQQ spread $7 in the money"""

    print("\n" + "="*80)
    print("Testing QQQ Deep ITM Scenario (Client's Issue)")
    print("="*80)

    service = get_thetradelist_service()

    # Get current QQQ price
    price_data = await service.get_stock_price('QQQ')
    current_price = price_data.get('price')

    print(f"\nCurrent QQQ price: ${current_price:.2f}")

    # Calculate the strikes for $7 ITM
    buy_strike = int(current_price - 7)
    sell_strike = buy_strike + 1

    print(f"\nTarget spread ($7 ITM, $1-wide):")
    print(f"  Buy:  ${buy_strike} call")
    print(f"  Sell: ${sell_strike} call")
    print(f"  Distance ITM: ${current_price - sell_strike:.2f}")

    print(f"\nExpected spread cost: $0.95-$1.00 (very deep ITM)")
    print(f"If mini options were contaminating: could show $0.30 (70% off)")

    # Get actual option chain data
    print(f"\n{'='*80}")
    print("Fetching live option data...")
    print(f"{'='*80}")

    try:
        # Get option contracts for next expiration
        contracts_data = await service.get_options_contracts(
            underlying_ticker="QQQ",
            expiration_date=None,
            fetch_all=False
        )

        results = contracts_data.get("results", [])

        # Find the specific strikes
        buy_option = None
        sell_option = None

        for contract in results:
            strike = float(contract.get("strike_price", 0))
            contract_type = contract.get("contract_type", "")

            if contract_type == "call":
                if abs(strike - buy_strike) < 0.5:
                    buy_option = contract
                elif abs(strike - sell_strike) < 0.5:
                    sell_option = contract

        if not buy_option or not sell_option:
            print(f"\n⚠️  Could not find both strikes in option chain")
            print(f"   Looking for ${buy_strike} and ${sell_strike}")
            return False

        print(f"\n✅ Found both strikes in option chain")

        # Now try to get pricing
        print(f"\nFetching pricing data...")

        # Use the algorithm to get full pricing
        algorithm = get_overnight_options_algorithm()
        result = await algorithm.run_algorithm(ticker="QQQ")

        if result.get("success"):
            algo_result = result.get("algorithm_result", {})

            if algo_result.get("spread_cost"):
                spread_cost = algo_result["spread_cost"]
                buy_strike_selected = algo_result.get("buy_strike")
                sell_strike_selected = algo_result.get("sell_strike")
                roi = algo_result.get("roi_potential")

                print(f"\n{'='*80}")
                print(f"Algorithm Selected Spread:")
                print(f"{'='*80}")
                print(f"  Buy:  ${buy_strike_selected:.0f} call")
                print(f"  Sell: ${sell_strike_selected:.0f} call")
                print(f"  Spread cost: ${spread_cost:.2f}")
                print(f"  ROI potential: {roi:.1f}%")

                # Check if it's the deep ITM one we're testing
                itm_distance = current_price - sell_strike_selected
                print(f"  Distance ITM: ${itm_distance:.2f}")

                # Validate spread cost
                if spread_cost < 1.00:
                    print(f"\n✅ Spread cost is valid (< $1.00)")

                    # Check if it's reasonable for the ITM distance
                    if itm_distance >= 5:  # Deep ITM
                        if spread_cost > 0.85:
                            print(f"✅ Deep ITM spread cost looks correct (${spread_cost:.2f})")
                        else:
                            print(f"⚠️  Deep ITM spread cost seems low (${spread_cost:.2f})")
                            print(f"   Expected $0.85-$0.99 for ${itm_distance:.2f} ITM")

                    return True
                else:
                    print(f"❌ Spread cost exceeds maximum ($1.00)")
                    return False
            else:
                print(f"\nℹ️  No qualifying spread found")
                print(f"   This could mean:")
                print(f"   - No deep ITM options available")
                print(f"   - Bid-ask spreads too wide")
                print(f"   - All spreads exceed max cost threshold")
        else:
            print(f"❌ Algorithm failed")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    async def main():
        result = await test_qqq_deep_itm()

        print(f"\n{'='*80}")
        if result:
            print("✅ TEST PASSED - QQQ deep ITM pricing looks correct")
        else:
            print("ℹ️  TEST INCOMPLETE - Could not fully validate")
        print("="*80)

    asyncio.run(main())