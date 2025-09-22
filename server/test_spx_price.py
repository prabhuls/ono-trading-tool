#!/usr/bin/env python3
"""
Test script to fetch current SPX price from TheTradeList API via ISIN
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add the server directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.external.thetradelist_service import TheTradeListService

async def test_spx_via_service():
    """Test SPX price retrieval using the service"""
    print("\n" + "="*60)
    print("TEST: SPX Price via TheTradeListService")
    print("="*60)

    service = TheTradeListService()

    print("\n📍 Service Configuration:")
    print(f"  Base URL: {service.base_url}")
    print(f"  Service Name: {service.service_name}")

    try:
        print("\n🔄 Calling get_stock_price('SPX')...")
        result = await service.get_stock_price("SPX")

        if result:
            print("\n✅ SUCCESS: Got SPX price data")
            print("\n📊 SPX Price Data:")
            print(f"  Ticker: {result.get('ticker')}")
            print(f"  Price: ${result.get('price', 0):,.2f}")
            print(f"  Change: ${result.get('change', 0):+.2f}")
            print(f"  Change %: {result.get('change_percent', 0):+.2f}%")
            print(f"  Timestamp: {result.get('timestamp')}")
            return result
        else:
            print("❌ No data returned from service")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

async def test_spx_direct_isin():
    """Test direct ISIN endpoint call for SPX"""
    print("\n" + "="*60)
    print("TEST: Direct ISIN API Call for SPX")
    print("="*60)

    import aiohttp
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Get API key
    api_key = os.getenv("THETRADELIST_API_KEY", "dbdaf77d-2e63-424f-943f-709c72289fad")
    base_url = "https://api.thetradelist.com/v1/data"

    # ISIN endpoint for SPX
    endpoint = "/v3/data/isin"
    url = f"{base_url}{endpoint}"

    params = {
        "isin": "US78378X1072",  # SPX ISIN
        "apiKey": api_key
    }

    print(f"\n📍 Direct API Call Details:")
    print(f"  URL: {url}")
    print(f"  ISIN: {params['isin']} (SPX)")
    print(f"  API Key: {api_key[:10]}...")

    try:
        async with aiohttp.ClientSession() as session:
            print("\n🔄 Making direct API request to ISIN endpoint...")
            async with session.get(url, params=params, timeout=30) as response:
                print(f"📊 Response Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print("\n✅ SUCCESS: Got response from ISIN endpoint")

                    # Show the raw response structure
                    print("\n📄 Raw ISIN Response:")
                    print(json.dumps(data, indent=2)[:800])

                    # Parse the ISIN response format
                    print("\n💰 SPX Price from ISIN:")
                    print(f"  Price: ${float(data.get('price', 0)):,.2f}")
                    print(f"  Change Absolute: ${data.get('change_absolute', 0):+.2f}")
                    print(f"  Change Percent: {data.get('change_percent', 0):+.2f}%")

                    if 'meta' in data:
                        print(f"  Name: {data['meta'].get('name', 'N/A')}")
                        print(f"  ID: {data['meta'].get('id', 'N/A')}")

                    return float(data.get('price', 0))
                else:
                    error = await response.text()
                    print(f"\n❌ API Error {response.status}")
                    print(f"Response: {error[:500]}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

async def main():
    """Run all SPX price tests"""
    print("\n" + "#"*60)
    print("# SPX Price Test - TheTradeList API")
    print("#"*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Using service
    service_result = await test_spx_via_service()

    # Test 2: Direct ISIN call
    direct_price = await test_spx_direct_isin()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if service_result:
        print(f"Service Method: SPX = ${service_result.get('price', 0):,.2f}")
    else:
        print("Service Method: Failed")

    if direct_price:
        print(f"Direct ISIN API: SPX = ${direct_price:,.2f}")
    else:
        print("Direct ISIN API: Failed")

    if service_result and direct_price:
        service_price = service_result.get('price', 0)
        if abs(service_price - direct_price) < 0.01:
            print("\n✅ Both methods returned the same price!")
        else:
            print(f"\n⚠️ Price difference: ${abs(service_price - direct_price):.2f}")

if __name__ == "__main__":
    asyncio.run(main())