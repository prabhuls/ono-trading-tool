"""
Quick test to verify duplicate handling
"""

# Simulate what happens with duplicate strikes
contracts = [
    {"strike": 6580, "contract_ticker": "O:SPX250919C06580000", "bid": 45.80, "ask": 46.30},
    {"strike": 6580, "contract_ticker": "O:SPXW250919C06580000", "bid": 41.80, "ask": 42.80},
    {"strike": 6585, "contract_ticker": "O:SPX250919C06585000", "bid": 42.30, "ask": 42.80},
    {"strike": 6585, "contract_ticker": "O:SPXW250919C06585000", "bid": 38.20, "ask": 38.20},
]

print("Testing duplicate strike handling:")
print(f"Total contracts: {len(contracts)}")

# Check strikes
strikes = [c["strike"] for c in contracts]
unique_strikes = set(strikes)
print(f"Unique strikes: {len(unique_strikes)}")

# Check contract tickers
tickers = [c["contract_ticker"] for c in contracts]
unique_tickers = set(tickers)
print(f"Unique tickers: {len(unique_tickers)}")

if len(tickers) == len(unique_tickers):
    print("✅ All contracts have unique tickers - React keys will work!")
    print("\nEach contract will use its ticker as the React key:")
    for c in contracts:
        print(f"  Strike {c['strike']} -> key={c['contract_ticker']}")
else:
    print("⚠️  Some contracts have duplicate tickers")

print("\n✅ Solution: Algorithm can select from all contracts, frontend uses unique ticker as key")