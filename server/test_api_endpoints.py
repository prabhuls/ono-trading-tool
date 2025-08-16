#!/usr/bin/env python3
"""
Test TheTradeList API endpoints to identify which are working/failing
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional

class APIEndpointTester:
    def __init__(self):
        self.base_url = "https://api.thetradelist.com/v1/data"
        self.api_key = "a599851f-e85e-4477-b6f5-ceb68850983c"  # PHP's key
        self.options_api_key = "5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5"
        self.test_symbol = "AAPL"
        self.results = []
        
    async def test_endpoint(self, name: str, url: str, params: Optional[Dict] = None, 
                          method: str = "GET", expect_format: str = "json") -> Dict:
        """Test a single endpoint"""
        result = {
            "endpoint": name,
            "url": url,
            "status": "UNKNOWN",
            "status_code": None,
            "response_type": None,
            "error": None,
            "sample_data": None
        }
        
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        if params:
            print(f"Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, params=params, timeout=30) as response:
                    result["status_code"] = response.status
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        result["response_type"] = content_type
                        
                        if expect_format == "csv" or 'csv' in content_type:
                            text = await response.text()
                            result["status"] = "SUCCESS"
                            # Get first few lines as sample
                            lines = text.strip().split('\n')[:3]
                            result["sample_data"] = '\n'.join(lines)
                            print(f"✓ SUCCESS (200) - CSV response")
                            print(f"Sample: {result['sample_data'][:200]}")
                        else:
                            try:
                                data = await response.json()
                                result["status"] = "SUCCESS"
                                result["sample_data"] = json.dumps(data, indent=2)[:500]
                                print(f"✓ SUCCESS (200) - JSON response")
                                print(f"Sample: {result['sample_data']}")
                            except:
                                text = await response.text()
                                result["status"] = "SUCCESS"
                                result["sample_data"] = text[:500]
                                print(f"✓ SUCCESS (200) - Text response")
                                print(f"Sample: {result['sample_data']}")
                    else:
                        text = await response.text()
                        result["status"] = "FAILED"
                        result["error"] = f"HTTP {response.status}: {text[:200]}"
                        print(f"✗ FAILED ({response.status})")
                        print(f"Response: {text[:200]}")
                        
        except asyncio.TimeoutError:
            result["status"] = "TIMEOUT"
            result["error"] = "Request timed out after 30 seconds"
            print(f"✗ TIMEOUT")
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            print(f"✗ ERROR: {e}")
        
        self.results.append(result)
        return result
    
    async def run_all_tests(self):
        """Test all endpoints from the PHP implementation"""
        print("=" * 80)
        print("Testing TheTradeList API Endpoints")
        print("=" * 80)
        
        # Test 1: Highs/Lows CSV endpoint (PHP primary)
        await self.test_endpoint(
            "Highs/Lows CSV",
            f"{self.base_url}/get_highs_lows.php/",
            {
                "price": "15.00",
                "volume": "500000",
                "extreme": "high",
                "returntype": "csv",
                "apiKey": self.api_key
            },
            expect_format="csv"
        )
        
        # Test 2: Quote endpoint (PHP fallback)
        await self.test_endpoint(
            "Quote",
            f"{self.base_url}/get_quote.php/",
            {
                "symbol": self.test_symbol,
                "returntype": "json",
                "apiKey": self.api_key
            }
        )
        
        # Test 3: Stock Info endpoint (PHP fallback)
        await self.test_endpoint(
            "Stock Info",
            f"{self.base_url}/get_stock_info.php/",
            {
                "symbol": self.test_symbol,
                "returntype": "json",
                "apiKey": self.api_key
            }
        )
        
        # Test 4: Polygon Historical Data (PHP uses for OHLCV)
        today = datetime.now().strftime("%Y-%m-%d")
        year_ago = "2024-01-15"
        await self.test_endpoint(
            "Polygon Historical",
            f"{self.base_url}/get_polygon.php/ticker/{self.test_symbol}/range/1/day/{year_ago}/{today}",
            {
                "adjusted": "true",
                "sort": "desc",
                "limit": "300",
                "apiKey": self.api_key
            }
        )
        
        # Test 5: Options Contracts (PHP uses for options analysis)
        await self.test_endpoint(
            "Options Contracts",
            f"{self.base_url}/options-contracts",
            {
                "underlying_ticker": self.test_symbol,
                "limit": "100",
                "apiKey": self.options_api_key
            }
        )
        
        # Test 6: Last Quote (for option quotes)
        await self.test_endpoint(
            "Last Quote (Options)",
            f"{self.base_url}/last-quote",
            {
                "ticker": f"{self.test_symbol}250117C00230000",  # Example option ticker
                "apiKey": self.options_api_key
            }
        )
        
        # Additional endpoints to verify
        
        # Test 7: Alternative highs/lows without trailing slash
        await self.test_endpoint(
            "Highs/Lows (no slash)",
            f"{self.base_url}/get_highs_lows.php",
            {
                "price": "15.00",
                "volume": "500000",
                "extreme": "low",
                "returntype": "csv",
                "apiKey": self.api_key
            },
            expect_format="csv"
        )
        
        # Test 8: Check if JSON format works for highs/lows
        await self.test_endpoint(
            "Highs/Lows JSON",
            f"{self.base_url}/get_highs_lows.php/",
            {
                "price": "15.00",
                "volume": "500000",
                "extreme": "high",
                "returntype": "json",
                "apiKey": self.api_key
            }
        )
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        working = []
        failing = []
        
        for result in self.results:
            status_icon = "✓" if result["status"] == "SUCCESS" else "✗"
            print(f"{status_icon} {result['endpoint']}: {result['status']} (HTTP {result['status_code']})")
            
            if result["status"] == "SUCCESS":
                working.append(result["endpoint"])
            else:
                failing.append(result["endpoint"])
        
        print("\n" + "-" * 40)
        print(f"WORKING ENDPOINTS ({len(working)}):")
        for endpoint in working:
            print(f"  ✓ {endpoint}")
        
        print(f"\nFAILING ENDPOINTS ({len(failing)}):")
        for endpoint in failing:
            print(f"  ✗ {endpoint}")
        
        # Save detailed results
        with open("api_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\nDetailed results saved to: api_test_results.json")
        
        return self.results

async def main():
    tester = APIEndpointTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())