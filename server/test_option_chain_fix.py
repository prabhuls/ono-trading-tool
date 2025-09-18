"""
Test script to verify option chain fetching gets strikes around current price
"""
import asyncio
from app.services.external.thetradelist_service import get_thetradelist_service
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_option_chain():
    """Test that option chain gets strikes both above and below current price"""
    print("\n" + "="*60)
    print("Testing Option Chain Fetching for SPX")
    print("="*60)

    service = get_thetradelist_service()

    try:
        # Get current SPX price
        price_data = await service.get_stock_price("SPX")
        current_price = price_data.get("price", 6600)
        print(f"\n📍 Current SPX price: ${current_price:.2f}")

        # Build option chain with pricing (as used by the UI)
        print("\n📊 Fetching option chain with pricing...")
        option_chain = await service.build_option_chain_with_pricing(
            ticker="SPX",
            expiration_date=None  # Use next trading day
        )

        contracts = option_chain.get("contracts", [])
        print(f"\n✅ Retrieved {len(contracts)} contracts")

        # Analyze strike distribution
        strikes_above = []
        strikes_below = []
        strikes_at = []

        for contract in contracts:
            strike = float(contract.get("strike", 0))
            if strike > current_price:
                strikes_above.append(strike)
            elif strike < current_price:
                strikes_below.append(strike)
            else:
                strikes_at.append(strike)

        # Get unique strikes
        unique_above = sorted(set(strikes_above))
        unique_below = sorted(set(strikes_below))

        print(f"\n📈 Strike Distribution:")
        print(f"   Strikes above ${current_price}: {len(unique_above)}")
        print(f"   Strikes at ${current_price}: {len(strikes_at)}")
        print(f"   Strikes below ${current_price}: {len(unique_below)}")

        if unique_above and unique_below:
            print(f"\n📊 Strike Range:")
            print(f"   Lowest strike: ${min(unique_below):.0f}")
            print(f"   Highest strike: ${max(unique_above):.0f}")

            # Show strikes near current price
            near_strikes = [s for s in unique_below if s >= current_price - 200] + \
                          [s for s in unique_above if s <= current_price + 200]
            near_strikes = sorted(near_strikes)[:10]

            print(f"\n📍 Sample strikes near ${current_price}:")
            for strike in near_strikes:
                diff = strike - current_price
                sign = "+" if diff > 0 else ""
                print(f"   ${strike:.0f} ({sign}{diff:.0f})")

        # Check if we have sufficient data for spread analysis
        if len(unique_below) >= 10 and len(unique_above) >= 10:
            print(f"\n✅ SUCCESS: Option chain has sufficient strikes on both sides!")
            print(f"   Ready for spread analysis with {len(unique_below)} strikes below and {len(unique_above)} strikes above")
        else:
            print(f"\n⚠️  WARNING: Insufficient strikes for spread analysis")
            print(f"   Need at least 10 strikes on each side of current price")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_option_chain())