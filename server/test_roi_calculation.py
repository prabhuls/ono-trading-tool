"""
Test ROI calculation issue - Compare SPX and SPY calculations
"""
import asyncio
from app.services.overnight_options_algorithm import get_overnight_options_algorithm

async def test_calculations():
    print("=== Testing Spread Calculations ===\n")

    # Test SPX calculation
    print("SPX CALCULATION TEST:")
    print("-" * 40)

    # Simulate SPX spread with actual values from screenshot
    # Buy 6580 Ask: $42.80, Sell 6585 Bid: $42.30
    spx_spread_cost = 42.80 - 42.30
    spx_max_value = 5.00  # $5 wide spread for SPX
    spx_max_reward = spx_max_value - spx_spread_cost
    spx_roi = (spx_max_reward / spx_spread_cost * 100) if spx_spread_cost > 0 else 0

    print(f"Buy Ask: $42.80, Sell Bid: $42.30")
    print(f"Spread Cost: ${spx_spread_cost:.2f}")
    print(f"Max Value (spread width): ${spx_max_value:.2f}")
    print(f"Max Reward: ${spx_max_reward:.2f}")
    print(f"ROI Potential: {spx_roi:.1f}%")
    print(f"Issue: ROI of {spx_roi:.1f}% is unrealistic!\n")

    # Test SPY calculation for comparison
    print("SPY CALCULATION TEST (for comparison):")
    print("-" * 40)

    # Typical SPY spread
    spy_buy_ask = 8.50
    spy_sell_bid = 7.80
    spy_spread_cost = spy_buy_ask - spy_sell_bid
    spy_max_value = 1.00  # $1 wide spread for SPY
    spy_max_reward = spy_max_value - spy_spread_cost
    spy_roi = (spy_max_reward / spy_spread_cost * 100) if spy_spread_cost > 0 else 0

    print(f"Buy Ask: ${spy_buy_ask:.2f}, Sell Bid: ${spy_sell_bid:.2f}")
    print(f"Spread Cost: ${spy_spread_cost:.2f}")
    print(f"Max Value (spread width): ${spy_max_value:.2f}")
    print(f"Max Reward: ${spy_max_reward:.2f}")
    print(f"ROI Potential: {spy_roi:.1f}%")
    print(f"This is more realistic: {spy_roi:.1f}%\n")

    # Check the algorithm service calculation
    print("ALGORITHM SERVICE TEST:")
    print("-" * 40)
    algo = get_overnight_options_algorithm()

    # Test with mock data
    mock_buy_option = {"ask": 42.80, "bid": 41.80, "strike": 6580}
    mock_sell_option = {"ask": 42.80, "bid": 42.30, "strike": 6585}

    spread_cost = algo.calculate_spread_cost(mock_buy_option, mock_sell_option, "SPX")
    metrics = algo.calculate_spread_metrics(spread_cost, "SPX")

    print(f"Algorithm Spread Cost: ${spread_cost:.2f}")
    print(f"Algorithm Max Reward: ${metrics['max_reward']:.2f}")
    print(f"Algorithm ROI: {metrics['roi_potential']:.1f}%")

    print("\n=== ANALYSIS ===")
    print("-" * 40)
    print("The issue is that the spread cost of $0.50 for SPX is unrealistically low.")
    print("This suggests either:")
    print("1. The bid/ask prices are incorrect or stale")
    print("2. The contracts are from different series with mismatched prices")
    print("3. There's a data synchronization issue")
    print("\nTypical SPX spread costs should be $2.00-$4.00 for reasonable ROI (25-150%)")
    print("A $0.50 spread cost giving 900% ROI indicates bad pricing data.")

if __name__ == "__main__":
    asyncio.run(test_calculations())