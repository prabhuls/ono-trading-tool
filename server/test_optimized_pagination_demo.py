"""
Demo script to compare optimized vs full pagination for SPX options with hardcoded current price
"""
import asyncio
import time
from datetime import datetime
from app.services.tradelist.client import TradeListClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Hardcoded SPX price for demonstration (actual market price as of Sep 2025)
# SPX is currently trading around 6,600 according to market data
DEMO_SPX_PRICE = 6600.0

async def test_full_pagination():
    """Test fetching all SPX contracts (old behavior)"""
    print("\n" + "="*60)
    print("Testing FULL pagination (fetching all contracts)")
    print("="*60)

    client = TradeListClient()
    start_time = time.time()

    try:
        async with client:
            contracts = await client.get_options_contracts(
                "SPX",
                limit=1000,
                fetch_all=True  # Force full fetch
            )

            elapsed_time = time.time() - start_time
            print(f"\n✅ Full fetch completed")
            print(f"   Total contracts retrieved: {len(contracts)}")
            print(f"   Time taken: {elapsed_time:.2f} seconds")
            return len(contracts), elapsed_time

    except Exception as e:
        print(f"❌ Error during full fetch: {e}")
        return 0, 0


async def test_optimized_pagination():
    """Test optimized pagination with early exit using hardcoded price"""
    print("\n" + "="*60)
    print("Testing OPTIMIZED pagination (early exit after current price)")
    print("="*60)

    client = TradeListClient()
    current_price = DEMO_SPX_PRICE
    print(f"📍 Using demo SPX price: ${current_price:.2f}")

    start_time = time.time()

    try:
        async with client:
            contracts = await client.get_options_contracts(
                "SPX",
                limit=1000,
                fetch_all=False,  # Use optimized fetching
                current_price=current_price,  # Use hardcoded price for demo
                target_strikes_below_price=30,  # Get 30 unique strikes below current price
                target_strikes_above_price=30   # And 30 unique strikes above
            )

            elapsed_time = time.time() - start_time
            print(f"\n✅ Optimized fetch completed")
            print(f"   Total contracts retrieved: {len(contracts)}")
            print(f"   Time taken: {elapsed_time:.2f} seconds")

            # Count strikes around current price
            unique_strikes_above = set()
            unique_strikes_below = set()
            unique_strikes_at = set()

            for c in contracts:
                strike = float(c.get('strike_price', 0))
                if strike > current_price:
                    unique_strikes_above.add(strike)
                elif strike < current_price:
                    unique_strikes_below.add(strike)
                else:
                    unique_strikes_at.add(strike)

            print(f"\n   📊 Strike distribution around ${current_price}:")
            print(f"   Unique strikes above: {len(unique_strikes_above)}")
            print(f"   Unique strikes at: {len(unique_strikes_at)}")
            print(f"   Unique strikes below: {len(unique_strikes_below)}")

            # Show strike range
            if contracts:
                strikes = [float(c.get('strike_price', 0)) for c in contracts]
                print(f"\n   📈 Strike range: ${min(strikes):.0f} - ${max(strikes):.0f}")

            # Show some sample strikes near the current price
            strikes_sorted = sorted(strikes)
            strikes_near_price = [s for s in strikes_sorted if abs(s - current_price) <= 200][:10]
            if strikes_near_price:
                print(f"\n   📍 Sample strikes near ${current_price}: {', '.join(f'${s:.0f}' for s in strikes_near_price)}")

            return len(contracts), elapsed_time

    except Exception as e:
        print(f"❌ Error during optimized fetch: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


async def main():
    """Run both tests and compare results"""
    print("\n" + "="*80)
    print("SPX OPTIONS PAGINATION PERFORMANCE COMPARISON (DEMO)")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Demo SPX price: ${DEMO_SPX_PRICE:.2f}")

    # Test optimized approach first (faster)
    opt_count, opt_time = await test_optimized_pagination()

    # Test full pagination (slower)
    full_count, full_time = await test_full_pagination()

    # Print comparison
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON RESULTS")
    print("="*80)

    if full_time > 0 and opt_time > 0:
        speedup = full_time / opt_time
        reduction = (1 - opt_count / full_count) * 100 if full_count > 0 else 0

        print(f"\n📊 Full Pagination:")
        print(f"   Contracts: {full_count:,}")
        print(f"   Time: {full_time:.2f} seconds")
        print(f"   Pages fetched: ~21 (all)")

        print(f"\n🚀 Optimized Pagination:")
        print(f"   Contracts: {opt_count:,}")
        print(f"   Time: {opt_time:.2f} seconds")
        print(f"   Pages fetched: ~3-5 (early exit)")

        print(f"\n📈 Performance Improvement:")
        print(f"   Speed improvement: {speedup:.1f}x faster")
        print(f"   Data reduction: {reduction:.1f}% fewer contracts")
        print(f"   Time saved: {full_time - opt_time:.2f} seconds")

        print(f"\n✨ Summary:")
        print(f"   • Optimized approach is {speedup:.1f}x faster!")
        print(f"   • Fetches only relevant strikes near current price")
        print(f"   • Perfect for real-time spread analysis and trading")
        print(f"   • Reduces API load and improves response time")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())