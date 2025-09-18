"""
Analyze SPX spreads from existing contract data
"""
import asyncio
import csv
from datetime import datetime, timedelta
from typing import List, Dict
from app.services.tradelist.client import TradeListClient
import logging
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def analyze_spx_spreads():
    """Analyze SPX spreads for $5-wide spreads with $3.75 max cost"""

    # Create TradeList client
    client = TradeListClient()

    print("Fetching SPX option contracts...")
    print("This will fetch all contracts and analyze potential spreads...")

    try:
        async with client:
            # Fetch all SPX contracts
            contracts = await client.get_options_contracts("SPX", limit=1000)
            print(f"\nTotal contracts retrieved: {len(contracts)}")

            if not contracts:
                print("No contracts retrieved!")
                return

            # Filter for near-term expirations (next 10 days)
            today = datetime.now().date()
            ten_days_from_now = today + timedelta(days=10)

            near_term_contracts = []
            for contract in contracts:
                exp_date_str = contract.get('expiration_date')
                if exp_date_str:
                    try:
                        exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                        if today <= exp_date <= ten_days_from_now:
                            near_term_contracts.append(contract)
                    except ValueError:
                        continue

            print(f"Near-term contracts (expiring within 10 days): {len(near_term_contracts)}")

            # Fetch quotes for a subset of near-term contracts
            print("\nFetching quotes for near-term contracts...")

            # Sample contracts to avoid overloading the API
            sample_size = min(100, len(near_term_contracts))  # Limit to 100 contracts
            sampled_contracts = random.sample(near_term_contracts, sample_size) if len(near_term_contracts) > sample_size else near_term_contracts

            contracts_with_quotes = []

            for i, contract in enumerate(sampled_contracts):
                ticker = contract.get('ticker')
                if ticker:
                    print(f"Fetching quote {i+1}/{len(sampled_contracts)}: {ticker}", end='\r')
                    quote = await client.get_option_quote(ticker)
                    if quote:
                        contract['bid'] = quote.get('bid_price', 0)
                        contract['ask'] = quote.get('ask_price', 0)
                        contract['last'] = quote.get('last_price', 0)
                        contract['volume'] = quote.get('volume', 0)
                        contract['open_interest'] = quote.get('open_interest', 0)
                        contract['implied_volatility'] = quote.get('implied_volatility', 0)
                    else:
                        # Use placeholder values if quote fails
                        contract['bid'] = 0
                        contract['ask'] = 0
                        contract['last'] = 0
                        contract['volume'] = 0
                        contract['open_interest'] = 0
                        contract['implied_volatility'] = 0

                    contracts_with_quotes.append(contract)

                    # Rate limiting
                    if i % 10 == 0:
                        await asyncio.sleep(0.5)

            print(f"\n\nSuccessfully fetched quotes for {len(contracts_with_quotes)} contracts")

            # Group by expiration and type
            expiration_groups = {}
            for contract in contracts_with_quotes:
                exp_date = contract.get('expiration_date')
                contract_type = contract.get('contract_type')
                key = (exp_date, contract_type)

                if key not in expiration_groups:
                    expiration_groups[key] = []
                expiration_groups[key].append(contract)

            # Calculate spreads
            spread_calculations = []
            spread_width = 5.0
            max_cost = 3.75

            for (exp_date, contract_type), contracts_list in expiration_groups.items():
                if contract_type != 'call':  # Focus on call spreads for now
                    continue

                # Sort by strike
                contracts_list.sort(key=lambda x: float(x.get('strike_price', 0)))

                # Find $5-wide spreads
                for i, buy_contract in enumerate(contracts_list):
                    buy_strike = float(buy_contract.get('strike_price', 0))
                    target_sell_strike = buy_strike + spread_width

                    # Find matching sell contract
                    sell_contract = None
                    for sell in contracts_list:
                        if abs(float(sell.get('strike_price', 0)) - target_sell_strike) < 0.01:
                            sell_contract = sell
                            break

                    if sell_contract:
                        buy_ask = float(buy_contract.get('ask', 0))
                        sell_bid = float(sell_contract.get('bid', 0))

                        # Skip if no pricing data
                        if buy_ask == 0 or sell_bid == 0:
                            continue

                        # Calculate spread metrics
                        spread_cost = buy_ask - sell_bid
                        max_profit = spread_width - spread_cost
                        roi = (max_profit / spread_cost * 100) if spread_cost > 0 else 0

                        spread_data = {
                            'expiration_date': exp_date,
                            'spread_type': 'Bull Call Spread',
                            'buy_strike': buy_strike,
                            'sell_strike': float(sell_contract.get('strike_price', 0)),
                            'buy_ticker': buy_contract.get('ticker'),
                            'sell_ticker': sell_contract.get('ticker'),
                            'buy_bid': float(buy_contract.get('bid', 0)),
                            'buy_ask': buy_ask,
                            'buy_last': float(buy_contract.get('last', 0)),
                            'sell_bid': sell_bid,
                            'sell_ask': float(sell_contract.get('ask', 0)),
                            'sell_last': float(sell_contract.get('last', 0)),
                            'spread_cost': round(spread_cost, 2),
                            'max_profit': round(max_profit, 2),
                            'max_loss': round(spread_cost, 2),
                            'roi_percent': round(roi, 2),
                            'meets_3.75_criteria': 'Yes' if 0 < spread_cost <= max_cost else 'No',
                            'buy_volume': buy_contract.get('volume', 0),
                            'sell_volume': sell_contract.get('volume', 0),
                            'buy_oi': buy_contract.get('open_interest', 0),
                            'sell_oi': sell_contract.get('open_interest', 0),
                            'buy_iv': round(float(buy_contract.get('implied_volatility', 0)) * 100, 2),
                            'sell_iv': round(float(sell_contract.get('implied_volatility', 0)) * 100, 2)
                        }

                        spread_calculations.append(spread_data)

            # Save all data to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed spread analysis
            if spread_calculations:
                spreads_filename = f"spx_spreads_detailed_{timestamp}.csv"
                with open(spreads_filename, 'w', newline='') as csvfile:
                    fieldnames = spread_calculations[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    # Sort by ROI
                    spread_calculations.sort(key=lambda x: x['roi_percent'], reverse=True)

                    for spread in spread_calculations:
                        writer.writerow(spread)

                print(f"\nSpread analysis saved to: {spreads_filename}")

                # Print summary
                valid_spreads = [s for s in spread_calculations if s['meets_3.75_criteria'] == 'Yes']
                print(f"\n=== SPREAD ANALYSIS SUMMARY ===")
                print(f"Total spreads analyzed: {len(spread_calculations)}")
                print(f"Spreads meeting $3.75 max cost: {len(valid_spreads)}")

                if valid_spreads:
                    print(f"\nTop 5 Recommended Spreads (by ROI):")
                    print("-" * 80)
                    for i, spread in enumerate(valid_spreads[:5]):
                        print(f"\n#{i+1} - Exp: {spread['expiration_date']} | ROI: {spread['roi_percent']}%")
                        print(f"  Buy {spread['buy_strike']} Call @ ${spread['buy_ask']}")
                        print(f"  Sell {spread['sell_strike']} Call @ ${spread['sell_bid']}")
                        print(f"  Net Cost: ${spread['spread_cost']} | Max Profit: ${spread['max_profit']}")
                        print(f"  Volume: Buy={spread['buy_volume']}, Sell={spread['sell_volume']}")
                        print(f"  OI: Buy={spread['buy_oi']}, Sell={spread['sell_oi']}")

            # Also save all contracts with pricing to a separate CSV
            all_contracts_filename = f"spx_all_contracts_with_pricing_{timestamp}.csv"
            if contracts_with_quotes:
                with open(all_contracts_filename, 'w', newline='') as csvfile:
                    fieldnames = ['ticker', 'underlying_ticker', 'strike_price', 'contract_type',
                                'expiration_date', 'bid', 'ask', 'last', 'volume', 'open_interest',
                                'implied_volatility']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()

                    for contract in contracts_with_quotes:
                        writer.writerow(contract)

                print(f"\nAll contracts with pricing saved to: {all_contracts_filename}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_spx_spreads())