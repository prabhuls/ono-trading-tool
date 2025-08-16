#!/usr/bin/env python3
"""
Test the Polygon endpoint with different tickers to see which work
"""

import asyncio
import aiohttp
import json

async def test_polygon_endpoint(symbol: str):
    """Test Polygon endpoint for a specific symbol"""
    base_url = "https://api.thetradelist.com/v1/data"
    api_key = "a599851f-e85e-4477-b6f5-ceb68850983c"
    
    # Test historical data endpoint
    url = f"{base_url}/get_polygon.php/ticker/{symbol}/range/1/day/2025-08-14/2025-08-15"
    params = {
        "adjusted": "true",
        "sort": "desc", 
        "limit": "10",
        "apiKey": api_key
    }
    
    full_url = f"{url}?adjusted={params['adjusted']}&sort={params['sort']}&limit={params['limit']}&apiKey={params['apiKey']}"
    
    print(f"\nTesting {symbol}:")
    print(f"URL: {full_url[:100]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                print(f"Status: {response.status}")
                print(f"Content-Type: {content_type}")
                
                if response.status == 200:
                    text = await response.text()
                    
                    # Check if it's JSON or HTML
                    if text.strip().startswith('{') or text.strip().startswith('['):
                        try:
                            data = json.loads(text)
                            if "results" in data and data["results"]:
                                print(f"✓ SUCCESS - Got {len(data['results'])} results")
                                latest = data['results'][0]
                                print(f"  Latest: Date={latest.get('t', 'N/A')}, Close=${latest.get('c', 0):.2f}")
                            else:
                                print(f"✓ JSON but no results")
                        except json.JSONDecodeError:
                            print(f"✗ Invalid JSON")
                    elif text.strip().startswith('<'):
                        print(f"✗ Got HTML instead of JSON")
                        print(f"  HTML snippet: {text[:200]}")
                    else:
                        print(f"? Unknown format")
                        print(f"  Response snippet: {text[:200]}")
                else:
                    text = await response.text()
                    print(f"✗ Failed with status {response.status}")
                    print(f"  Response: {text[:200]}")
                    
    except Exception as e:
        print(f"✗ Error: {e}")

async def main():
    print("=" * 80)
    print("Testing Polygon Endpoint with Different Tickers")
    print("=" * 80)
    
    # Test different types of tickers
    test_symbols = [
        "AAPL",    # Regular stock
        "MSFT",    # Another regular stock
        "SPY",     # ETF
        "ACWX",    # The problematic ETF from earlier
        "TSLA",    # Popular stock
        "QQQ",     # Popular ETF
        "NVDA",    # High-volume stock
    ]
    
    for symbol in test_symbols:
        await test_polygon_endpoint(symbol)
    
    print("\n" + "=" * 80)
    print("Summary:")
    print("The Polygon endpoint may not support all tickers (especially ETFs)")
    print("Consider filtering for stocks only or handling HTML responses")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())