"""
Test that duplicate strikes are allowed but have unique keys
"""
import asyncio
from app.services.external.thetradelist_service import get_thetradelist_service
from collections import Counter

async def test():
    service = get_thetradelist_service()
    result = await service.build_option_chain_with_pricing('SPX')
    contracts = result.get('contracts', [])

    # Check for duplicate strikes
    strikes = [c['strike'] for c in contracts]
    unique_strikes = set(strikes)

    print(f'Total contracts: {len(contracts)}')
    print(f'Total strikes: {len(strikes)}')
    print(f'Unique strikes: {len(unique_strikes)}')

    if len(strikes) != len(unique_strikes):
        print(f'\nFound {len(strikes) - len(unique_strikes)} duplicate strikes (this is OK now)')

        # Show which strikes are duplicated
        strike_counts = Counter(strikes)
        duplicates = [(strike, count) for strike, count in strike_counts.items() if count > 1]

        print(f'Strikes with multiple contracts: {len(duplicates)}')
        for strike, count in duplicates[:5]:  # Show first 5
            print(f'  Strike {strike} appears {count} times')
    else:
        print('No duplicate strikes found')

    # Check that all contracts have unique tickers
    tickers = [c.get('contract_ticker', '') for c in contracts]
    unique_tickers = set(tickers)
    print(f'\nContract tickers: {len(tickers)} total, {len(unique_tickers)} unique')

    if len(tickers) == len(unique_tickers):
        print('✅ All contracts have unique tickers - React keys will work!')
    else:
        print('⚠️  Some contracts missing unique tickers')

if __name__ == "__main__":
    asyncio.run(test())