"""
Test the new validation logic for unrealistic spreads
"""
import asyncio
from app.services.overnight_options_algorithm import get_overnight_options_algorithm

async def test():
    algo = get_overnight_options_algorithm(max_cost_threshold=3.75)

    print("=== Testing Spread Validation ===\n")

    # Test case 1: Unrealistic SPX spread (too cheap)
    print("Test 1: SPX spread with $0.50 cost (should be rejected)")
    mock_buy = {"ask": 42.80, "bid": 41.80, "strike": 6580, "contract_ticker": "O:SPX250919C06580000"}
    mock_sell = {"ask": 42.80, "bid": 42.30, "strike": 6585, "contract_ticker": "O:SPXW250919C06585000"}

    cost = algo.calculate_spread_cost(mock_buy, mock_sell, "SPX")
    print(f"Calculated cost: ${cost:.2f}")
    print(f"Result: {'REJECTED' if cost == 0 else 'ACCEPTED'}\n")

    # Test case 2: Realistic SPX spread
    print("Test 2: SPX spread with $2.50 cost (should be accepted)")
    mock_buy2 = {"ask": 42.80, "bid": 40.00, "strike": 6580, "contract_ticker": "O:SPX250919C06580000"}
    mock_sell2 = {"ask": 41.00, "bid": 40.30, "strike": 6585, "contract_ticker": "O:SPX250919C06585000"}

    cost2 = algo.calculate_spread_cost(mock_buy2, mock_sell2, "SPX")
    metrics2 = algo.calculate_spread_metrics(cost2, "SPX") if cost2 > 0 else None
    print(f"Calculated cost: ${cost2:.2f}")
    if metrics2:
        print(f"ROI: {metrics2['roi_potential']}%")
        print(f"Max Reward: ${metrics2['max_reward']}")
    print(f"Result: {'ACCEPTED' if cost2 > 0 else 'REJECTED'}\n")

    # Test case 3: SPY spread (lower threshold)
    print("Test 3: SPY spread with $0.25 cost (should be rejected)")
    mock_buy3 = {"ask": 8.50, "bid": 8.20, "strike": 658, "contract_ticker": "O:SPY250919C00658000"}
    mock_sell3 = {"ask": 8.30, "bid": 8.25, "strike": 659, "contract_ticker": "O:SPY250919C00659000"}

    cost3 = algo.calculate_spread_cost(mock_buy3, mock_sell3, "SPY")
    print(f"Calculated cost: ${cost3:.2f}")
    print(f"Result: {'REJECTED' if cost3 == 0 else 'ACCEPTED'}\n")

    # Test case 4: ROI capping
    print("Test 4: Testing ROI capping at 200%")
    test_cost = 1.60  # For $5 spread, this gives 212.5% ROI
    metrics4 = algo.calculate_spread_metrics(test_cost, "SPX")
    print(f"Spread cost: ${test_cost}")
    print(f"Calculated ROI: {((5.0 - test_cost) / test_cost * 100):.1f}%")
    print(f"Capped ROI: {metrics4['roi_potential']}%")
    print(f"Result: ROI {'CAPPED at 200%' if metrics4['roi_potential'] == 200.0 else 'NOT CAPPED'}\n")

if __name__ == "__main__":
    asyncio.run(test())