"""
Test script to verify mini options are filtered correctly
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.external.thetradelist_service import get_thetradelist_service


async def test_mini_options_filter():
    """Test that mini options are filtered out for GLD, IWM, QQQ"""

    service = get_thetradelist_service()

    print("\n" + "="*80)
    print("Testing Mini Options Filter")
    print("="*80)

    for ticker in ["GLD", "IWM", "QQQ"]:
        print(f"\n{'='*80}")
        print(f"Testing {ticker}")
        print(f"{'='*80}")

        try:
            # Get option contracts
            contracts_data = await service.get_options_contracts(
                underlying_ticker=ticker,
                expiration_date=None,  # Get next available
                fetch_all=False
            )

            results = contracts_data.get("results", [])
            print(f"\nTotal contracts retrieved: {len(results)}")

            # Check for any mini options that might have slipped through
            mini_options_found = []
            standard_options = []

            for contract in results:
                ticker_symbol = contract.get("ticker", "")
                if ticker_symbol:
                    # Check for mini option pattern: O:TICKER7YYMMDD...
                    if ":" in ticker_symbol:
                        symbol_part = ticker_symbol.split(":")[1]
                        ticker_len = len(ticker)
                        if ticker_len < len(symbol_part) and symbol_part[ticker_len] == "7":
                            mini_options_found.append(ticker_symbol)
                        else:
                            standard_options.append(ticker_symbol)
                    else:
                        standard_options.append(ticker_symbol)

            print(f"Standard options: {len(standard_options)}")
            print(f"Mini options (should be 0): {len(mini_options_found)}")

            if mini_options_found:
                print(f"\n⚠️  WARNING: Mini options were not filtered!")
                print(f"Sample mini options found: {mini_options_found[:5]}")
                return False
            else:
                print(f"✅ SUCCESS: No mini options found - filter working correctly!")

            # Show sample contract tickers
            if standard_options:
                print(f"\nSample standard contracts:")
                for i, contract_ticker in enumerate(standard_options[:5]):
                    print(f"  {i+1}. {contract_ticker}")

        except Exception as e:
            print(f"\n❌ ERROR testing {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    print(f"\n{'='*80}")
    print("✅ All tests passed! Mini options filter is working correctly.")
    print("="*80)
    return True


async def test_spread_cost_validation():
    """Test that spread costs are reasonable after filtering"""

    service = get_thetradelist_service()

    print("\n" + "="*80)
    print("Testing Spread Cost Validation")
    print("="*80)

    from app.services.overnight_options_algorithm import get_overnight_options_algorithm

    for ticker in ["GLD", "IWM", "QQQ"]:
        print(f"\n{'='*80}")
        print(f"Testing spread cost for {ticker}")
        print(f"{'='*80}")

        try:
            algorithm = get_overnight_options_algorithm()
            result = await algorithm.run_algorithm(ticker=ticker)

            if result.get("success"):
                algo_result = result.get("algorithm_result", {})
                spread_cost = algo_result.get("spread_cost")

                if spread_cost:
                    print(f"✅ Spread cost: ${spread_cost:.2f}")

                    # Validate spread cost is reasonable (< $1.00 for these ETFs)
                    if spread_cost < 1.00:
                        print(f"✅ Spread cost is valid (< $1.00)")
                    else:
                        print(f"⚠️  WARNING: Spread cost seems high (>= $1.00)")
                        return False

                    # Check ROI
                    roi = algo_result.get("roi_potential")
                    if roi:
                        print(f"   ROI potential: {roi:.1f}%")

                else:
                    print(f"ℹ️  No qualifying spread found (may be normal)")
            else:
                print(f"⚠️  Algorithm did not succeed for {ticker}")

        except Exception as e:
            print(f"❌ ERROR testing {ticker} spread cost: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    print(f"\n{'='*80}")
    print("✅ Spread cost validation passed!")
    print("="*80)
    return True


if __name__ == "__main__":
    async def main():
        # Test 1: Check mini options are filtered
        test1_passed = await test_mini_options_filter()

        if test1_passed:
            # Test 2: Check spread costs are reasonable
            test2_passed = await test_spread_cost_validation()

            if test1_passed and test2_passed:
                print("\n" + "="*80)
                print("🎉 ALL TESTS PASSED!")
                print("="*80)
                sys.exit(0)
            else:
                print("\n" + "="*80)
                print("❌ SOME TESTS FAILED")
                print("="*80)
                sys.exit(1)
        else:
            print("\n" + "="*80)
            print("❌ TESTS FAILED")
            print("="*80)
            sys.exit(1)

    asyncio.run(main())