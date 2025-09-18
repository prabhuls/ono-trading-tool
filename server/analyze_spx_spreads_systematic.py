"""
Systematically analyze SPX spreads for $5-wide spreads with bid/ask data
"""
import asyncio
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.services.tradelist.client import TradeListClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def analyze_spx_spreads_systematic():
    """Systematically analyze SPX spreads for $5-wide spreads"""

    # Create TradeList client
    client = TradeListClient()

    print("Fetching SPX option contracts...")
    print("This will systematically analyze potential $5-wide spreads with $3.75 max cost...")

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

            # Group contracts by expiration and type
            expiration_groups = {}
            for contract in contracts:
                exp_date_str = contract.get('expiration_date')
                if not exp_date_str:
                    continue

                try:
                    exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                    if today <= exp_date <= ten_days_from_now:
                        contract_type = contract.get('contract_type')
                        key = (exp_date_str, contract_type)

                        if key not in expiration_groups:
                            expiration_groups[key] = []
                        expiration_groups[key].append(contract)
                except ValueError:
                    continue

            print(f"\nFound {len(expiration_groups)} expiration/type combinations within 10 days")

            # Process each expiration's call options
            spread_calculations = []
            all_contracts_with_pricing = []
            spread_width = 5.0
            max_cost = 3.75

            for (exp_date, contract_type), contracts_list in expiration_groups.items():
                if contract_type != 'call':  # Focus on call spreads
                    continue

                print(f"\nProcessing {exp_date} calls ({len(contracts_list)} contracts)...")

                # Sort by strike
                contracts_list.sort(key=lambda x: float(x.get('strike_price', 0)))

                # Find the middle range (around ATM)
                # Assuming SPX is around 5600-5700, focus on strikes from 5500-5800
                filtered_contracts = [
                    c for c in contracts_list
                    if 5500 <= float(c.get('strike_price', 0)) <= 5800
                ]

                if not filtered_contracts:
                    # If no contracts in expected range, take middle 50 contracts
                    mid = len(contracts_list) // 2
                    start = max(0, mid - 25)
                    end = min(len(contracts_list), mid + 25)
                    filtered_contracts = contracts_list[start:end]

                print(f"  Analyzing {len(filtered_contracts)} contracts around ATM...")

                # Create a map of strikes to contracts for quick lookup
                strike_map = {float(c.get('strike_price', 0)): c for c in filtered_contracts}

                # Fetch quotes for contracts that can form $5-wide spreads
                contracts_to_quote = []
                for contract in filtered_contracts:
                    buy_strike = float(contract.get('strike_price', 0))
                    sell_strike = buy_strike + spread_width

                    # Check if we have the matching sell strike
                    if sell_strike in strike_map:
                        contracts_to_quote.append(contract)
                        contracts_to_quote.append(strike_map[sell_strike])

                # Remove duplicates
                unique_tickers = set()
                unique_contracts = []
                for c in contracts_to_quote:
                    ticker = c.get('ticker')
                    if ticker not in unique_tickers:
                        unique_tickers.add(ticker)
                        unique_contracts.append(c)

                print(f"  Fetching quotes for {len(unique_contracts)} unique contracts...")

                # Fetch quotes
                for i, contract in enumerate(unique_contracts):
                    ticker = contract.get('ticker')
                    if ticker:
                        if (i + 1) % 10 == 0:
                            print(f"    Progress: {i+1}/{len(unique_contracts)}", end='\r')

                        quote = await client.get_option_quote(ticker)
                        if quote:
                            contract['bid'] = quote.get('bid_price', 0)
                            contract['ask'] = quote.get('ask_price', 0)
                            contract['last'] = quote.get('last_price', 0)
                            contract['volume'] = quote.get('volume', 0)
                            contract['open_interest'] = quote.get('open_interest', 0)
                            contract['implied_volatility'] = quote.get('implied_volatility', 0)
                            all_contracts_with_pricing.append(contract)
                        else:
                            contract['bid'] = 0
                            contract['ask'] = 0
                            contract['last'] = 0
                            contract['volume'] = 0
                            contract['open_interest'] = 0
                            contract['implied_volatility'] = 0

                        # Update strike map with pricing
                        strike_map[float(contract.get('strike_price', 0))] = contract

                        # Rate limiting
                        if i % 5 == 0:
                            await asyncio.sleep(0.2)

                print(f"\n  Calculating spreads for {exp_date}...")

                # Calculate spreads with the fetched quotes
                for buy_strike in sorted(strike_map.keys()):
                    sell_strike = buy_strike + spread_width

                    if sell_strike not in strike_map:
                        continue

                    buy_contract = strike_map[buy_strike]
                    sell_contract = strike_map[sell_strike]

                    buy_ask = float(buy_contract.get('ask', 0))
                    sell_bid = float(sell_contract.get('bid', 0))

                    # Skip if no pricing data or invalid spread
                    if buy_ask <= 0 or sell_bid <= 0 or buy_ask <= sell_bid:
                        continue

                    # Calculate spread metrics
                    spread_cost = round(buy_ask - sell_bid, 2)
                    max_profit = round(spread_width - spread_cost, 2)
                    roi = round((max_profit / spread_cost * 100), 2) if spread_cost > 0 else 0

                    spread_data = {
                        'expiration_date': exp_date,
                        'spread_type': 'Bull Call Spread',
                        'buy_strike': buy_strike,
                        'sell_strike': sell_strike,
                        'buy_ticker': buy_contract.get('ticker'),
                        'sell_ticker': sell_contract.get('ticker'),
                        'buy_bid': float(buy_contract.get('bid', 0)),
                        'buy_ask': buy_ask,
                        'buy_last': float(buy_contract.get('last', 0)),
                        'sell_bid': sell_bid,
                        'sell_ask': float(sell_contract.get('ask', 0)),
                        'sell_last': float(sell_contract.get('last', 0)),
                        'spread_cost': spread_cost,
                        'max_profit': max_profit,
                        'max_loss': spread_cost,
                        'roi_percent': roi,
                        'meets_3.75_criteria': 'Yes' if 0 < spread_cost <= max_cost else 'No',
                        'buy_volume': buy_contract.get('volume', 0),
                        'sell_volume': sell_contract.get('volume', 0),
                        'buy_oi': buy_contract.get('open_interest', 0),
                        'sell_oi': sell_contract.get('open_interest', 0),
                        'buy_iv': round(float(buy_contract.get('implied_volatility', 0)) * 100, 2),
                        'sell_iv': round(float(sell_contract.get('implied_volatility', 0)) * 100, 2)
                    }

                    spread_calculations.append(spread_data)

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save spread analysis
            if spread_calculations:
                spreads_filename = f"spx_spreads_systematic_{timestamp}.csv"

                # Sort by ROI first
                spread_calculations.sort(key=lambda x: x['roi_percent'], reverse=True)

                with open(spreads_filename, 'w', newline='') as csvfile:
                    fieldnames = spread_calculations[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for spread in spread_calculations:
                        writer.writerow(spread)

                print(f"\n\nSpread analysis saved to: {spreads_filename}")

                # Print summary
                valid_spreads = [s for s in spread_calculations if s['meets_3.75_criteria'] == 'Yes']
                print(f"\n{'='*80}")
                print(f"SPREAD ANALYSIS SUMMARY")
                print(f"{'='*80}")
                print(f"Total spreads analyzed: {len(spread_calculations)}")
                print(f"Spreads meeting $3.75 max cost: {len(valid_spreads)}")

                # Group by expiration
                exp_summary = {}
                for spread in valid_spreads:
                    exp = spread['expiration_date']
                    if exp not in exp_summary:
                        exp_summary[exp] = []
                    exp_summary[exp].append(spread)

                print(f"\nBy Expiration:")
                for exp in sorted(exp_summary.keys()):
                    print(f"  {exp}: {len(exp_summary[exp])} valid spreads")

                if valid_spreads:
                    print(f"\n{'='*80}")
                    print(f"TOP 10 RECOMMENDED SPREADS (by ROI)")
                    print(f"{'='*80}")

                    for i, spread in enumerate(valid_spreads[:10]):
                        print(f"\n#{i+1} | Expiration: {spread['expiration_date']} | ROI: {spread['roi_percent']}%")
                        print(f"  Buy  {spread['buy_strike']} Call @ ${spread['buy_ask']:.2f} (Bid: ${spread['buy_bid']:.2f})")
                        print(f"  Sell {spread['sell_strike']} Call @ ${spread['sell_bid']:.2f} (Ask: ${spread['sell_ask']:.2f})")
                        print(f"  Net Cost: ${spread['spread_cost']:.2f} | Max Profit: ${spread['max_profit']:.2f}")
                        print(f"  Volume: Buy={spread['buy_volume']:,} | Sell={spread['sell_volume']:,}")
                        print(f"  Open Interest: Buy={spread['buy_oi']:,} | Sell={spread['sell_oi']:,}")
                        print(f"  IV: Buy={spread['buy_iv']:.1f}% | Sell={spread['sell_iv']:.1f}%")

            # Save all contracts with pricing
            if all_contracts_with_pricing:
                contracts_filename = f"spx_contracts_with_quotes_{timestamp}.csv"
                with open(contracts_filename, 'w', newline='') as csvfile:
                    fieldnames = ['ticker', 'underlying_ticker', 'strike_price', 'contract_type',
                                'expiration_date', 'bid', 'ask', 'last', 'volume', 'open_interest',
                                'implied_volatility']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()

                    for contract in all_contracts_with_pricing:
                        writer.writerow(contract)

                print(f"\nAll contracts with pricing saved to: {contracts_filename}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_spx_spreads_systematic())