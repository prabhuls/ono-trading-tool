#!/usr/bin/env python3
"""
Trace the actual SPX ISIN API call with debug logging
"""
import asyncio
import sys
from pathlib import Path
import logging

# Add the server directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable debug logging for httpx
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s | %(name)s | %(message)s')
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)

from app.services.external.thetradelist_service import TheTradeListService

async def trace_spx_call():
    """Trace the SPX ISIN call with full debug"""
    print("\n" + "="*60)
    print("Tracing SPX ISIN API Call")
    print("="*60)

    service = TheTradeListService()

    print("\n📍 Service Details:")
    print(f"  Base URL: {service.base_url}")
    print(f"  API Key: {service.api_key[:10]}...")

    try:
        print("\n🔄 Calling get_spx_price_via_isin()...")
        result = await service.get_spx_price_via_isin()

        print("\n✅ SUCCESS!")
        print(f"  SPX Price: ${result.get('price', 0):,.2f}")
        print(f"  Change: ${result.get('change', 0):+.2f}")
        print(f"  Change %: {result.get('change_percent', 0):+.2f}%")

        return result

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    return None

if __name__ == "__main__":
    asyncio.run(trace_spx_call())