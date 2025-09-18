"""
Quick test to check contract structure
"""
import asyncio
from app.services.external.thetradelist_service import get_thetradelist_service

async def test():
    service = get_thetradelist_service()

    # Build option chain
    option_chain = await service.build_option_chain_with_pricing(
        ticker="SPX",
        expiration_date=None
    )

    contracts = option_chain.get("contracts", [])
    print(f"Total contracts: {len(contracts)}")

    if contracts:
        print(f"\nFirst contract:")
        for key, value in contracts[0].items():
            print(f"  {key}: {value}")

        # Check strike field names
        strikes = []
        for c in contracts:
            if "strike" in c:
                strikes.append(c["strike"])
            elif "strike_price" in c:
                strikes.append(c["strike_price"])

        print(f"\nFound {len(strikes)} strikes")
        if strikes:
            print(f"Strike range: ${min(strikes)} - ${max(strikes)}")

if __name__ == "__main__":
    asyncio.run(test())