#!/usr/bin/env python3
"""
Test natural pricing implementation in Credit Spread Scanner
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from app.services.credit_spread_scanner import CreditSpreadScanner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_natural_pricing_calculation():
    """Test that natural pricing is used instead of mid-price"""
    print("=" * 80)
    print("TESTING CREDIT SPREAD SCANNER - NATURAL PRICING")
    print("=" * 80)
    
    # Create scanner instance
    scanner = CreditSpreadScanner()
    
    # Mock data for testing
    sell_contract = {
        'strike_price': '100',
        'expiration_date': '2024-12-20',
        'ticker': 'SPY_241220C100'
    }
    
    buy_contract = {
        'strike_price': '105',  
        'expiration_date': '2024-12-20',
        'ticker': 'SPY_241220C105'
    }
    
    # Mock quote data - designed to show difference between natural and mid pricing
    sell_quote = {
        'bid_price': '2.40',  # We receive this when selling
        'ask_price': '2.50'   # Mid would be 2.45
    }
    
    buy_quote = {
        'bid_price': '1.80',  # Mid would be 1.85
        'ask_price': '1.90'   # We pay this when buying
    }
    
    # Mock the quote fetching method
    async def mock_get_cached_quote(ticker):
        if 'C100' in ticker:  # sell contract
            return sell_quote
        elif 'C105' in ticker:  # buy contract
            return buy_quote
        return None
    
    scanner.get_cached_quote = mock_get_cached_quote
    
    print("\nTest Data:")
    print(f"Sell Contract (100 strike): Bid={sell_quote['bid_price']}, Ask={sell_quote['ask_price']}")
    print(f"Buy Contract (105 strike):  Bid={buy_quote['bid_price']}, Ask={buy_quote['ask_price']}")
    
    # Calculate what the results should be
    natural_credit = float(sell_quote['bid_price']) - float(buy_quote['ask_price'])  # 2.40 - 1.90 = 0.50
    mid_credit = ((float(sell_quote['bid_price']) + float(sell_quote['ask_price'])) / 2) - \
                 ((float(buy_quote['bid_price']) + float(buy_quote['ask_price'])) / 2)  # 2.45 - 1.85 = 0.60
    
    print(f"\nExpected Results:")
    print(f"Natural Pricing Credit: ${natural_credit:.2f} (conservative)")
    print(f"Mid-Price Credit:       ${mid_credit:.2f} (optimistic)")
    print(f"Difference:             ${mid_credit - natural_credit:.2f}")
    
    # Test the actual calculation
    try:
        result = await scanner.calculate_credit_spread_metrics(
            sell_contract=sell_contract,
            buy_contract=buy_contract, 
            current_price=98.50,  # Below strikes for put credit spread
            trend='uptrend',
            option_type='call'
        )
        
        if result and result.get('net_credit'):
            actual_credit = result['net_credit']
            print(f"\nActual Result:")
            print(f"Net Credit: ${actual_credit}")
            
            # Verify we're using natural pricing
            if abs(actual_credit - natural_credit) < 0.01:
                print("✅ SUCCESS: Using natural pricing (conservative approach)")
                print(f"   Expected: ${natural_credit:.2f}, Got: ${actual_credit:.2f}")
            elif abs(actual_credit - mid_credit) < 0.01:
                print("❌ FAIL: Still using mid-price (not updated correctly)")
                print(f"   Expected natural: ${natural_credit:.2f}, Got mid-price: ${actual_credit:.2f}")
            else:
                print("⚠️  UNEXPECTED: Got different value than expected")
                print(f"   Expected natural: ${natural_credit:.2f}")
                print(f"   Expected mid: ${mid_credit:.2f}")
                print(f"   Actually got: ${actual_credit:.2f}")
            
            # Show other metrics
            print(f"\nOther Metrics:")
            print(f"Max Risk: ${result.get('max_risk', 'N/A')}")
            print(f"ROI: {result.get('roi_percent', 'N/A')}%")
            print(f"Breakeven: ${result.get('breakeven', 'N/A')}")
            
        else:
            print("❌ FAIL: No result returned or missing net_credit")
            if result:
                print(f"Result keys: {list(result.keys())}")
            
    except Exception as e:
        print(f"❌ ERROR during calculation: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
    
    print("\n" + "=" * 80)

async def test_bid_ask_spread_validation():
    """Test that wide bid-ask spreads are rejected"""
    print("\nTESTING BID-ASK SPREAD WIDTH VALIDATION")
    print("-" * 60)
    
    scanner = CreditSpreadScanner()
    
    # Test case: unreasonably wide bid-ask spread (should be rejected)
    sell_contract = {
        'strike_price': '100',
        'expiration_date': '2024-12-20', 
        'ticker': 'TEST_241220C100'
    }
    
    buy_contract = {
        'strike_price': '105',
        'expiration_date': '2024-12-20',
        'ticker': 'TEST_241220C105'
    }
    
    # Very wide spreads (>10% of $5 spread width = >$0.50)
    wide_sell_quote = {
        'bid_price': '2.00',
        'ask_price': '3.00'  # $1.00 spread = 20% of $5 width - should be rejected
    }
    
    wide_buy_quote = {
        'bid_price': '1.00',
        'ask_price': '1.30'  # $0.30 spread = 6% of $5 width - acceptable
    }
    
    async def mock_get_cached_quote_wide(ticker):
        if 'C100' in ticker:
            return wide_sell_quote
        elif 'C105' in ticker:
            return wide_buy_quote
        return None
    
    scanner.get_cached_quote = mock_get_cached_quote_wide
    
    print("Testing wide bid-ask spread rejection:")
    print(f"Sell option spread: ${float(wide_sell_quote['ask_price']) - float(wide_sell_quote['bid_price']):.2f} ({(1.00/5)*100:.0f}% of spread width)")
    print(f"Buy option spread:  ${float(wide_buy_quote['ask_price']) - float(wide_buy_quote['bid_price']):.2f} ({(0.30/5)*100:.0f}% of spread width)")
    
    try:
        result = await scanner.calculate_credit_spread_metrics(
            sell_contract=sell_contract,
            buy_contract=buy_contract,
            current_price=98.50,
            trend='uptrend', 
            option_type='call'
        )
        
        if result is None:
            print("✅ SUCCESS: Wide bid-ask spread correctly rejected")
        else:
            print("❌ FAIL: Wide bid-ask spread not rejected")
            print(f"Got result: {result}")
            
    except Exception as e:
        print(f"❌ ERROR during validation test: {e}")
    
    print("-" * 60)

async def main():
    """Run all tests"""
    try:
        await test_natural_pricing_calculation()
        await test_bid_ask_spread_validation()
        print("\n🎯 TESTING COMPLETE")
        print("   Check results above to verify natural pricing implementation")
        
    except Exception as e:
        logger.error(f"Testing failed: {e}", exc_info=True)
        print(f"\n❌ TESTING FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())