#!/usr/bin/env python3
"""
Trace the actual service call for SPY price
"""
import asyncio
import sys
from pathlib import Path
import logging

# Add the server directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s | %(name)s | %(message)s')

# Import the service
from app.services.external.thetradelist_service import TheTradeListService

async def trace_spy_call():
    """Trace the service call with debug logging"""
    print("\n" + "="*60)
    print("Tracing TheTradeListService.get_stock_price('SPY')")
    print("="*60)

    service = TheTradeListService()

    print("\n📍 Service Configuration:")
    print(f"  Base URL: {service.base_url}")
    print(f"  API Key: {service.api_key[:10]}...")
    print(f"  Service Name: {service.service_name}")

    try:
        print("\n🔄 Calling get_stock_price('SPY')...")
        result = await service.get_stock_price("SPY")

        print("\n✅ SUCCESS!")
        print(f"  Price: ${result.get('price', 0):.2f}")
        print(f"  Change: ${result.get('change', 0):+.2f}")
        print(f"  Change %: {result.get('change_percent', 0):+.2f}%")

        return result

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

if __name__ == "__main__":
    asyncio.run(trace_spy_call())