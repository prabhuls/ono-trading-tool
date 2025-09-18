"""
Test script to fetch SPX contracts with pricing and find optimal spreads
"""
import asyncio
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from app.services.tradelist.client import TradeListClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def fetch_spx_spreads_with_pricing():
    """Fetch SPX contracts with pricing and calculate optimal spreads"""

    # Create TradeList client
    client = TradeListClient()

    print("Fetching SPX option contracts with pricing data...")
    print("This may take several minutes due to pagination and quote fetching...")

    try:
        async with client:
            # Step 1: Fetch all SPX contracts
            contracts = await client.get_options_contracts("SPX", limit=1000)
            print(f"\nTotal contracts retrieved: {len(contracts)}")

            if not contracts:
                print("No contracts retrieved!")
                return

            # Step 2: Filter for near-term expirations (next 10 days)
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

            # Step 3: Group by expiration date
            expiration_groups = {}
            for contract in near_term_contracts:
                exp_date = contract.get('expiration_date')
                if exp_date not in expiration_groups:
                    expiration_groups[exp_date] = []
                expiration_groups[exp_date].append(contract)

            # Step 4: Process each expiration date
            all_spread_data = []

            for exp_date in sorted(expiration_groups.keys()):
                print(f"\nProcessing expiration: {exp_date}")
                contracts_for_date = expiration_groups[exp_date]

                # Separate calls and puts
                calls = [c for c in contracts_for_date if c.get('contract_type') == 'call']
                puts = [c for c in contracts_for_date if c.get('contract_type') == 'put']

                print(f"  Calls: {len(calls)}, Puts: {len(puts)}")

                # Sort by strike price
                calls.sort(key=lambda x: float(x.get('strike_price', 0)))
                puts.sort(key=lambda x: float(x.get('strike_price', 0)))

                # Fetch quotes for a sample of contracts (to avoid overwhelming the API)
                # We'll focus on ATM strikes for demonstration
                sample_size = min(20, len(calls))  # Limit to 20 contracts per type
                middle_idx = len(calls) // 2
                start_idx = max(0, middle_idx - sample_size // 2)
                end_idx = min(len(calls), start_idx + sample_size)

                sample_calls = calls[start_idx:end_idx]
                sample_puts = puts[start_idx:end_idx]

                # Fetch quotes for calls
                print(f"  Fetching quotes for {len(sample_calls)} call contracts...")
                for i, contract in enumerate(sample_calls):
                    ticker = contract.get('ticker')
                    if ticker:
                        quote = await client.get_option_quote(ticker)
                        if quote:
                            contract['bid'] = quote.get('bid_price', 0)
                            contract['ask'] = quote.get('ask_price', 0)
                            contract['last'] = quote.get('last_price', 0)
                            contract['volume'] = quote.get('volume', 0)
                            contract['open_interest'] = quote.get('open_interest', 0)
                        else:
                            contract['bid'] = 0
                            contract['ask'] = 0
                            contract['last'] = 0

                    # Add a small delay to avoid rate limiting
                    if i % 10 == 0:
                        await asyncio.sleep(0.1)

                # Fetch quotes for puts
                print(f"  Fetching quotes for {len(sample_puts)} put contracts...")
                for i, contract in enumerate(sample_puts):
                    ticker = contract.get('ticker')
                    if ticker:
                        quote = await client.get_option_quote(ticker)
                        if quote:
                            contract['bid'] = quote.get('bid_price', 0)
                            contract['ask'] = quote.get('ask_price', 0)
                            contract['last'] = quote.get('last_price', 0)
                            contract['volume'] = quote.get('volume', 0)
                            contract['open_interest'] = quote.get('open_interest', 0)
                        else:
                            contract['bid'] = 0
                            contract['ask'] = 0
                            contract['last'] = 0

                    # Add a small delay to avoid rate limiting
                    if i % 10 == 0:
                        await asyncio.sleep(0.1)

                # Step 5: Calculate spreads (for $5-wide spreads with $3.75 max cost)
                spread_width = 5.0
                max_cost = 3.75

                # Process call spreads (bull call spreads)
                for i, buy_call in enumerate(sample_calls):
                    buy_strike = float(buy_call.get('strike_price', 0))
                    buy_ask = float(buy_call.get('ask', 0))

                    if buy_ask == 0:
                        continue

                    # Find the sell call that's $5 higher
                    sell_strike = buy_strike + spread_width
                    sell_call = None

                    for call in sample_calls:
                        if abs(float(call.get('strike_price', 0)) - sell_strike) < 0.01:
                            sell_call = call
                            break

                    if sell_call:
                        sell_bid = float(sell_call.get('bid', 0))

                        # Calculate spread cost
                        spread_cost = buy_ask - sell_bid

                        # Calculate max profit (spread width - cost)
                        max_profit = spread_width - spread_cost

                        # Calculate ROI
                        roi = (max_profit / spread_cost * 100) if spread_cost > 0 else 0

                        spread_data = {
                            'expiration_date': exp_date,
                            'type': 'Bull Call Spread',
                            'buy_strike': buy_strike,
                            'sell_strike': sell_strike,
                            'buy_ticker': buy_call.get('ticker'),
                            'sell_ticker': sell_call.get('ticker'),
                            'buy_ask': buy_ask,
                            'sell_bid': sell_bid,
                            'spread_cost': round(spread_cost, 2),
                            'max_profit': round(max_profit, 2),
                            'max_loss': round(spread_cost, 2),
                            'roi_percent': round(roi, 2),
                            'meets_criteria': 'Yes' if spread_cost <= max_cost and spread_cost > 0 else 'No',
                            'buy_volume': buy_call.get('volume', 0),
                            'sell_volume': sell_call.get('volume', 0),
                            'buy_oi': buy_call.get('open_interest', 0),
                            'sell_oi': sell_call.get('open_interest', 0)
                        }

                        all_spread_data.append(spread_data)

                # Process put spreads (bear put spreads)
                for i, buy_put in enumerate(sample_puts):
                    buy_strike = float(buy_put.get('strike_price', 0))
                    buy_ask = float(buy_put.get('ask', 0))

                    if buy_ask == 0:
                        continue

                    # Find the sell put that's $5 lower
                    sell_strike = buy_strike - spread_width
                    sell_put = None

                    for put in sample_puts:
                        if abs(float(put.get('strike_price', 0)) - sell_strike) < 0.01:
                            sell_put = put
                            break

                    if sell_put:
                        sell_bid = float(sell_put.get('bid', 0))

                        # Calculate spread cost
                        spread_cost = buy_ask - sell_bid

                        # Calculate max profit (spread width - cost)
                        max_profit = spread_width - spread_cost

                        # Calculate ROI
                        roi = (max_profit / spread_cost * 100) if spread_cost > 0 else 0

                        spread_data = {
                            'expiration_date': exp_date,
                            'type': 'Bear Put Spread',
                            'buy_strike': buy_strike,
                            'sell_strike': sell_strike,
                            'buy_ticker': buy_put.get('ticker'),
                            'sell_ticker': sell_put.get('ticker'),
                            'buy_ask': buy_ask,
                            'sell_bid': sell_bid,
                            'spread_cost': round(spread_cost, 2),
                            'max_profit': round(max_profit, 2),
                            'max_loss': round(spread_cost, 2),
                            'roi_percent': round(roi, 2),
                            'meets_criteria': 'Yes' if spread_cost <= max_cost and spread_cost > 0 else 'No',
                            'buy_volume': buy_put.get('volume', 0),
                            'sell_volume': sell_put.get('volume', 0),
                            'buy_oi': buy_put.get('open_interest', 0),
                            'sell_oi': sell_put.get('open_interest', 0)
                        }

                        all_spread_data.append(spread_data)

            # Step 6: Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"spx_spreads_analysis_{timestamp}.csv"

            if all_spread_data:
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = all_spread_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    # Sort by ROI descending
                    all_spread_data.sort(key=lambda x: x['roi_percent'], reverse=True)

                    for spread in all_spread_data:
                        writer.writerow(spread)

                print(f"\n=== Spread Analysis Complete ===")
                print(f"Total spreads analyzed: {len(all_spread_data)}")

                # Filter for spreads meeting criteria
                valid_spreads = [s for s in all_spread_data if s['meets_criteria'] == 'Yes']
                print(f"Spreads meeting criteria (≤$3.75 cost): {len(valid_spreads)}")

                if valid_spreads:
                    print(f"\nTop 5 spreads by ROI:")
                    for i, spread in enumerate(valid_spreads[:5]):
                        print(f"\n{i+1}. {spread['type']} - Exp: {spread['expiration_date']}")
                        print(f"   Buy {spread['buy_strike']} / Sell {spread['sell_strike']}")
                        print(f"   Cost: ${spread['spread_cost']}, Max Profit: ${spread['max_profit']}")
                        print(f"   ROI: {spread['roi_percent']}%")

                print(f"\nFull analysis saved to: {filename}")
            else:
                print("No spread data to save!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fetch_spx_spreads_with_pricing())