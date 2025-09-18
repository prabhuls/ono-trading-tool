"""
Test script to verify option chain fetching with proper error handling
"""
import asyncio
from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.external.base import ExternalAPIError
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_option_chain():
    """Test option chain fetching with optimized pagination"""
    print("\n" + "="*60)
    print("Testing Optimized Option Chain Fetching for SPX")
    print("="*60)

    service = get_thetradelist_service()

    try:
        # Test 1: Normal operation with price available
        print("\n📊 Test 1: Fetching option chain with optimization...")

        # Build option chain with pricing (as used by the UI)
        option_chain = await service.build_option_chain_with_pricing(
            ticker="SPX",
            expiration_date=None  # Use next trading day
        )

        contracts = option_chain.get("contracts", [])
        print(f"✅ Retrieved {len(contracts)} contracts")

        # Debug: print first contract to see field names
        if contracts:
            print(f"\n🔍 Debug - First contract fields: {list(contracts[0].keys())}")

        # Get current price from the first step (it's validated there)
        price_data = await service.get_stock_price("SPX")
        current_price = price_data.get("price", 0)

        if current_price:
            print(f"📍 Current SPX price: ${current_price:.2f}")

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
            print(f"   Unique strikes above ${current_price}: {len(unique_above)}")
            print(f"   Unique strikes at ${current_price}: {len(strikes_at)}")
            print(f"   Unique strikes below ${current_price}: {len(unique_below)}")

            if unique_above and unique_below:
                print(f"\n📊 Strike Range:")
                print(f"   Lowest strike: ${min(unique_below):.0f}")
                print(f"   Highest strike: ${max(unique_above):.0f}")

                # Show strikes near current price
                near_strikes = [s for s in unique_below if s >= current_price - 200] + \
                              [s for s in unique_above if s <= current_price + 200]
                near_strikes = sorted(set(near_strikes))[:10]

                if near_strikes:
                    print(f"\n📍 Sample strikes near ${current_price}:")
                    for strike in near_strikes:
                        diff = strike - current_price
                        sign = "+" if diff > 0 else ""
                        print(f"   ${strike:.0f} ({sign}{diff:.0f})")

            # Check if we have sufficient data for spread analysis
            if len(unique_below) >= 10 and len(unique_above) >= 10:
                print(f"\n✅ SUCCESS: Option chain optimized correctly!")
                print(f"   {len(unique_below)} strikes below and {len(unique_above)} strikes above current price")
                print(f"   Ready for spread analysis")
            else:
                print(f"\n⚠️  WARNING: May need more strikes for complete analysis")
                print(f"   Consider increasing target_strikes_around_price parameter")

    except ExternalAPIError as e:
        print(f"\n❌ Expected API Error: {e.message}")
        print("   This would happen if the price cannot be retrieved")
        print("   The application correctly fails fast without showing incorrect data")

    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(test_option_chain())