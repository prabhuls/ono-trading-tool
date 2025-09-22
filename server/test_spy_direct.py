#!/usr/bin/env python3
"""
Direct test of TheTradeList API for SPY price
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def test_spy_price():
    """Direct API test with hardcoded API key from the service"""
    print(f"\n🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # API key from the service configuration
    api_key = "c03e9c84-f518-42cf-8453-e95ad5754234"

    # Construct URL
    url = "https://api.thetradelist.com/v1/data/snapshot-locale"

    params = {
        "tickers": "SPY,",
        "apiKey": api_key
    }

    print(f"📍 Endpoint: {url}")
    print(f"📦 Tickers: {params['tickers']}")
    print(f"🔑 API Key: {api_key[:10]}...")

    try:
        async with aiohttp.ClientSession() as session:
            print("\n🔄 Making request to TheTradeList API...")
            async with session.get(url, params=params, timeout=30) as response:
                print(f"📊 Response Status: {response.status}")

                if response.status == 200:
                    # First get the response as text to see what we're getting
                    response_text = await response.text()

                    # Check if it's JSON or HTML
                    if response_text.strip().startswith('<'):
                        print("\n⚠️  Got HTML response instead of JSON:")
                        print(response_text[:500])
                        return None

                    # Try to parse as JSON
                    import json
                    data = json.loads(response_text)

                    # Show response structure
                    print("\n📋 Response Structure:")
                    print(f"  - Status: {data.get('status')}")
                    print(f"  - Count: {data.get('count')}")
                    print(f"  - Has tickers: {len(data.get('tickers', []))} tickers")

                    # Find SPY data
                    tickers = data.get("tickers", [])
                    for ticker_data in tickers:
                        if ticker_data.get("ticker") == "SPY":
                            print("\n✅ SPY Data Found!")
                            print("="*60)

                            # Show raw ticker data structure
                            print("\n📄 Raw SPY Data Structure:")
                            print(json.dumps(ticker_data, indent=2)[:800])

                            # Extract key fields
                            day = ticker_data.get("day", {})
                            prev_day = ticker_data.get("prevDay", {})

                            # Calculate current price
                            current_close = day.get("c", 0)
                            prev_close = prev_day.get("c", 0)

                            # The current price is the latest close if available
                            current_price = current_close if current_close else prev_close

                            print("\n💰 SPY Price Information:")
                            print(f"  Current Price: ${current_price:.2f}")
                            print(f"  Previous Close: ${prev_close:.2f}")

                            if prev_close:
                                change = current_price - prev_close
                                change_pct = (change / prev_close) * 100
                                print(f"  Change: ${change:+.2f}")
                                print(f"  Change %: {change_pct:+.2f}%")

                            print("\n📊 Today's Trading Data:")
                            print(f"  Open: ${day.get('o', 0):.2f}")
                            print(f"  High: ${day.get('h', 0):.2f}")
                            print(f"  Low: ${day.get('l', 0):.2f}")
                            print(f"  Close: ${day.get('c', 0):.2f}")
                            print(f"  Volume: {day.get('v', 0):,}")

                            return current_price

                    print("❌ SPY not found in response")
                    print("Available tickers:", [t.get("ticker") for t in tickers])
                else:
                    error = await response.text()
                    print(f"\n❌ API Error {response.status}")
                    print(f"Response: {error[:500]}")

    except asyncio.TimeoutError:
        print("\n❌ Request timeout")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

if __name__ == "__main__":
    price = asyncio.run(test_spy_price())

    print("\n" + "="*60)
    if price:
        print(f"✅ Final Result: SPY is trading at ${price:.2f}")
    else:
        print("❌ Failed to get SPY price")