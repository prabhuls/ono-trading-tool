"""
Test that only the specific selected contracts are highlighted,
not all contracts with the same strike price
"""
import asyncio
import json
from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.overnight_options_algorithm import get_overnight_options_algorithm

async def test():
    # Get services
    tradelist_service = get_thetradelist_service()
    algorithm_service = get_overnight_options_algorithm(max_cost_threshold=3.75)

    # Run the algorithm for SPX
    result = await algorithm_service.run_algorithm('SPX')

    # Check the algorithm result
    algorithm_result = result.get('algorithm_result', {})
    buy_strike = algorithm_result.get('buy_strike')
    sell_strike = algorithm_result.get('sell_strike')

    print(f"\n=== Algorithm Result ===")
    print(f"Selected Buy Strike: {buy_strike}")
    print(f"Selected Sell Strike: {sell_strike}")
    print(f"Qualified Spreads: {algorithm_result.get('qualified_spreads_count')}")

    # Check the contracts for highlighting
    contracts = result.get('data', [])

    # Group contracts by strike to see duplicates
    strike_groups = {}
    for contract in contracts:
        strike = contract['strike']
        if strike not in strike_groups:
            strike_groups[strike] = []
        strike_groups[strike].append(contract)

    # Check strikes with duplicates
    print(f"\n=== Strike Analysis ===")
    for strike in sorted(strike_groups.keys()):
        if len(strike_groups[strike]) > 1:
            print(f"\nStrike {strike} has {len(strike_groups[strike])} contracts:")
            for i, contract in enumerate(strike_groups[strike], 1):
                ticker = contract.get('contract_ticker', 'N/A')
                highlighted = contract.get('is_highlighted')
                bid = contract.get('bid')
                ask = contract.get('ask')
                highlight_status = f"[{highlighted.upper()}]" if highlighted else ""
                print(f"  {i}. {ticker}: Bid=${bid}, Ask=${ask} {highlight_status}")

    # Verify only one contract per strike is highlighted
    print(f"\n=== Highlighting Verification ===")
    buy_contracts = [c for c in contracts if c.get('is_highlighted') == 'buy']
    sell_contracts = [c for c in contracts if c.get('is_highlighted') == 'sell']

    print(f"Total BUY highlighted contracts: {len(buy_contracts)}")
    if buy_contracts:
        for c in buy_contracts:
            print(f"  - Strike {c['strike']}: {c.get('contract_ticker', 'N/A')}")

    print(f"Total SELL highlighted contracts: {len(sell_contracts)}")
    if sell_contracts:
        for c in sell_contracts:
            print(f"  - Strike {c['strike']}: {c.get('contract_ticker', 'N/A')}")

    # Success criteria
    success = len(buy_contracts) == 1 and len(sell_contracts) == 1

    print(f"\n=== Test Result ===")
    if success:
        print("✅ SUCCESS: Only one specific contract highlighted for BUY and SELL")
    else:
        print("❌ FAILURE: Multiple contracts highlighted for same strike")

    return success

if __name__ == "__main__":
    asyncio.run(test())