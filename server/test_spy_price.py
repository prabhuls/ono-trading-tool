#!/usr/bin/env python3
"""
Test script to fetch current SPY price from TheTradeList API
"""
import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the server directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_direct_api_call():
    """Test direct API call to TheTradeList snapshot endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Direct API Call to TheTradeList")
    print("="*60)

    # Get API key from environment
    api_key = os.getenv("THETRADELIST_API_KEY", "")
    if not api_key:
        print("❌ ERROR: THETRADELIST_API_KEY not found in environment")
        return None

    print(f"✓ API Key found: {api_key[:8]}...")

    # Construct the URL
    base_url = "https://api.thetradelist.com/v1/data"
    endpoint = "/v2/aggs/snapshot-locale"
    url = f"{base_url}{endpoint}"

    params = {
        "tickers": "SPY,",  # Note the comma after SPY
        "apiKey": api_key
    }

    print(f"📍 URL: {url}")
    print(f"📦 Parameters: tickers={params['tickers']}")

    try:
        async with aiohttp.ClientSession() as session:
            print("\n🔄 Making API request...")
            async with session.get(url, params=params, timeout=30) as response:
                print(f"📊 Response Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print("✅ SUCCESS: Got response from API")

                    # Pretty print the full response
                    print("\n📄 Full Response:")
                    print(json.dumps(data, indent=2)[:1000])  # Limit output

                    # Extract SPY data
                    tickers = data.get("tickers", [])
                    if tickers:
                        for ticker_data in tickers:
                            if ticker_data.get("ticker") == "SPY":
                                print("\n🎯 SPY Data Found:")
                                print(f"  Ticker: {ticker_data.get('ticker')}")

                                # Calculate current price from day data
                                day = ticker_data.get("day", {})
                                prev_close = ticker_data.get("prevDay", {}).get("c", 0)
                                current_close = day.get("c", 0)

                                # Current price is the latest close or previous close
                                current_price = current_close if current_close else prev_close

                                print(f"  Current Price: ${current_price:.2f}")
                                print(f"  Day Open: ${day.get('o', 0):.2f}")
                                print(f"  Day High: ${day.get('h', 0):.2f}")
                                print(f"  Day Low: ${day.get('l', 0):.2f}")
                                print(f"  Day Close: ${day.get('c', 0):.2f}")
                                print(f"  Previous Close: ${prev_close:.2f}")
                                print(f"  Volume: {day.get('v', 0):,}")

                                # Calculate change
                                if prev_close and current_price:
                                    change = current_price - prev_close
                                    change_pct = (change / prev_close) * 100
                                    print(f"  Change: ${change:+.2f} ({change_pct:+.2f}%)")

                                return current_price
                    else:
                        print("❌ No ticker data in response")
                else:
                    error_text = await response.text()
                    print(f"❌ API Error: Status {response.status}")
                    print(f"   Error: {error_text[:200]}")

    except asyncio.TimeoutError:
        print("❌ Request timeout after 30 seconds")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

async def test_service_method():
    """Test using the existing TheTradeListService"""
    print("\n" + "="*60)
    print("TEST 2: Using TheTradeListService.get_stock_price()")
    print("="*60)

    try:
        from app.services.external.thetradelist_service import TheTradeListService

        service = TheTradeListService()
        print("✓ Service initialized")

        print("\n🔄 Fetching SPY price...")
        result = await service.get_stock_price("SPY")

        if result:
            print("✅ SUCCESS: Got price data")
            print("\n📊 SPY Price Data:")
            print(f"  Ticker: {result.get('ticker')}")
            print(f"  Price: ${result.get('price', 0):.2f}")
            print(f"  Change: ${result.get('change', 0):+.2f}")
            print(f"  Change %: {result.get('change_percent', 0):+.2f}%")
            print(f"  Timestamp: {result.get('timestamp')}")
            return result.get('price')
        else:
            print("❌ No data returned from service")

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure you're running from the server directory")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

async def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# SPY Price Test - TheTradeList API")
    print("#"*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Direct API call
    price1 = await test_direct_api_call()

    # Test 2: Using service
    price2 = await test_service_method()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Direct API Price: ${price1:.2f}" if price1 else "Direct API Price: Failed")
    print(f"Service Method Price: ${price2:.2f}" if price2 else "Service Method Price: Failed")

    if price1 and price2:
        if abs(price1 - price2) < 0.01:
            print("✅ Both methods returned the same price!")
        else:
            print(f"⚠️  Price difference: ${abs(price1 - price2):.2f}")

if __name__ == "__main__":
    asyncio.run(main())