"""
Credit Spread Detection Service
Adapted from CashFlowAgent for trend-based credit spread analysis
Uses TheTradeList API for options data
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class CreditSpreadDetector:
    """Handles trend-based credit spread detection with authentic pricing"""
    
    def __init__(self):
        self.tradelist_api_key = os.environ.get('TRADELIST_API_KEY', '5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5')
        self.base_url = "https://api.thetradelist.com/v1/data"
        self.api_call_count = 0
        self.max_api_calls = 2000
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def find_best_credit_spread(self, symbol: str, current_price: float, trend: str) -> Dict:
        """Main function to find best credit spread based on trend direction"""
        try:
            self.api_call_count = 0
            logger.info(f"Starting {trend} credit spread analysis for {symbol} at ${current_price}")
            
            # Step 1: Get all option contracts
            all_contracts = await self.get_all_contracts(symbol)
            if not all_contracts:
                return {'found': False, 'reason': 'No option contracts available'}
            
            # Step 2: Filter to closest valid expiration (minimum 3 DTE)
            closest_expiration_contracts = self.filter_to_closest_expiration(all_contracts)
            if not closest_expiration_contracts:
                return {'found': False, 'reason': 'No valid expirations found (minimum 3 DTE)'}
            
            # Step 3: Filter by option type based on trend
            # CREDIT SPREAD LOGIC:
            # Uptrend = Sell PUT spreads (bullish, expect price to stay above strikes)
            # Downtrend = Sell CALL spreads (bearish, expect price to stay below strikes)
            option_type = 'put' if trend == 'uptrend' else 'call'
            filtered_contracts = [c for c in closest_expiration_contracts 
                                if c.get('contract_type', '').lower() == option_type]
            
            if not filtered_contracts:
                return {'found': False, 'reason': f'No {option_type} contracts found for closest expiration'}
            
            # Step 4: Get strike selection based on trend
            sell_strike, buy_strike = self.get_safety_first_strikes(
                filtered_contracts, current_price, option_type, trend
            )
            
            if not sell_strike or not buy_strike:
                return {'found': False, 'reason': 'No suitable strike prices found with safety margin'}
            
            # Step 5: Get quotes for selected strikes (parallel)
            sell_contract = next((c for c in filtered_contracts if c['strike_price'] == sell_strike), None)
            buy_contract = next((c for c in filtered_contracts if c['strike_price'] == buy_strike), None)
            
            if not sell_contract or not buy_contract:
                return {'found': False, 'reason': 'Could not find contracts for selected strikes'}
            
            # Get quotes in parallel
            sell_quote_task = self.get_option_quote(sell_contract['ticker'])
            buy_quote_task = self.get_option_quote(buy_contract['ticker'])
            
            sell_quote, buy_quote = await asyncio.gather(sell_quote_task, buy_quote_task)
            
            if not sell_quote or not buy_quote:
                return {'found': False, 'reason': 'Could not get quotes for selected strikes'}
            
            # Step 6: Calculate credit spread metrics
            net_credit = sell_quote['bid'] - buy_quote['ask']
            
            if net_credit <= 0:
                return {'found': False, 'reason': 'No positive credit available (bid/ask spread too wide)'}
            
            max_risk = abs(sell_strike - buy_strike) - net_credit
            roi_percent = (net_credit / max_risk) * 100 if max_risk > 0 else 0
            
            # Apply ROI filter (7-15% target range)
            if roi_percent < 7:
                return {'found': False, 'reason': f'ROI too low: {roi_percent:.1f}% (minimum 7%)'}
            if roi_percent > 15:
                # Still return but flag as higher risk
                logger.warning(f"High ROI detected: {roi_percent:.1f}% - may indicate higher risk")
            
            # Calculate safety margins
            if option_type == 'put':
                safety_margin = ((current_price - sell_strike) / current_price) * 100
                safety_description = f"{safety_margin:.1f}% below current price"
            else:
                safety_margin = ((sell_strike - current_price) / current_price) * 100
                safety_description = f"{safety_margin:.1f}% above current price"
            
            # Build result
            expiration = sell_contract.get('expiration_date', '')
            dte = self.calculate_dte(expiration)
            
            result = {
                'found': True,
                'spread_type': f'{option_type}_credit',
                'expiration': expiration,
                'dte': dte,
                'sell_strike': sell_strike,
                'buy_strike': buy_strike,
                'sell_contract': sell_contract['ticker'],
                'buy_contract': buy_contract['ticker'],
                'sell_bid': sell_quote['bid'],
                'buy_ask': buy_quote['ask'],
                'net_credit': round(net_credit, 2),
                'max_risk': round(max_risk, 2),
                'max_profit': round(net_credit, 2),
                'roi_percent': round(roi_percent, 1),
                'breakeven': sell_strike - net_credit if option_type == 'put' else sell_strike + net_credit,
                'safety_margin': safety_description,
                'quote_calls_used': self.api_call_count
            }
            
            logger.info(f"Found {trend} credit spread for {symbol}: {roi_percent:.1f}% ROI, {safety_description}")
            return result
            
        except Exception as e:
            logger.error(f"Error finding credit spread for {symbol}: {str(e)}")
            return {'found': False, 'reason': f'Analysis error: {str(e)}'}
    
    async def get_all_contracts(self, symbol: str) -> List[Dict]:
        """Fetch all option contracts for a symbol"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/options-contracts"
            params = {
                'underlying_ticker': symbol,
                'limit': 1000,
                'apiKey': self.tradelist_api_key
            }
            
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    self.api_call_count += 1
                    
                    # Extract contracts from response
                    if isinstance(data, dict) and 'results' in data:
                        return data['results']
                    elif isinstance(data, list):
                        return data
                    else:
                        return []
                else:
                    logger.error(f"Failed to get contracts for {symbol}: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching contracts for {symbol}: {str(e)}")
            return []
    
    def filter_to_closest_expiration(self, contracts: List[Dict]) -> List[Dict]:
        """Filter contracts to closest valid expiration (minimum 3 DTE)"""
        today = datetime.now().date()
        min_date = today + timedelta(days=3)  # Minimum 3 DTE
        
        valid_expirations = {}
        for contract in contracts:
            exp_str = contract.get('expiration_date', '')
            if exp_str:
                try:
                    exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                    if exp_date >= min_date:
                        if exp_str not in valid_expirations:
                            valid_expirations[exp_str] = []
                        valid_expirations[exp_str].append(contract)
                except:
                    continue
        
        if not valid_expirations:
            return []
        
        # Get closest expiration
        closest_exp = min(valid_expirations.keys())
        return valid_expirations[closest_exp]
    
    def get_safety_first_strikes(self, contracts: List[Dict], current_price: float, 
                                option_type: str, trend: str) -> Tuple[Optional[float], Optional[float]]:
        """Select strikes with safety-first approach"""
        strikes = sorted(list(set(c['strike_price'] for c in contracts)))
        
        if option_type == 'put':
            # For puts: sell below current price
            valid_strikes = [s for s in strikes if s < current_price * 0.98]  # At least 2% below
            if len(valid_strikes) < 2:
                return None, None
            
            # Select strikes with good spacing
            sell_strike = valid_strikes[-1]  # Highest valid strike (closest to current)
            buy_strikes = [s for s in valid_strikes if s < sell_strike - 2.5]  # Minimum $2.50 spread
            
            if not buy_strikes:
                return None, None
            
            buy_strike = buy_strikes[-1]  # Highest available below sell
            
        else:  # call
            # For calls: sell above current price
            valid_strikes = [s for s in strikes if s > current_price * 1.02]  # At least 2% above
            if len(valid_strikes) < 2:
                return None, None
            
            # Select strikes with good spacing
            sell_strike = valid_strikes[0]  # Lowest valid strike (closest to current)
            buy_strikes = [s for s in valid_strikes if s > sell_strike + 2.5]  # Minimum $2.50 spread
            
            if not buy_strikes:
                return None, None
            
            buy_strike = buy_strikes[0]  # Lowest available above sell
        
        return sell_strike, buy_strike
    
    async def get_option_quote(self, option_ticker: str) -> Optional[Dict]:
        """Get quote for specific option contract"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/last-quote"
            params = {
                'ticker': option_ticker,
                'apiKey': self.tradelist_api_key
            }
            
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    self.api_call_count += 1
                    
                    # Parse response
                    if isinstance(data, dict) and 'results' in data:
                        results = data['results']
                        if isinstance(results, list) and len(results) > 0:
                            quote = results[0]
                            return {
                                'bid': float(quote.get('bid_price', 0) or quote.get('bid', 0)),
                                'ask': float(quote.get('ask_price', 0) or quote.get('ask', 0)),
                                'last': float(quote.get('last_price', 0) or quote.get('last', 0))
                            }
                    
                    # Fallback for direct response
                    if isinstance(data, dict) and 'bid' in data:
                        return {
                            'bid': float(data.get('bid', 0)),
                            'ask': float(data.get('ask', 0)),
                            'last': float(data.get('last', 0))
                        }
                    
                    return None
                else:
                    logger.error(f"Failed to get quote for {option_ticker}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching quote for {option_ticker}: {str(e)}")
            return None
    
    def calculate_dte(self, expiration_date: str) -> int:
        """Calculate days to expiration"""
        try:
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
            today = datetime.now().date()
            return (exp_date - today).days
        except:
            return 0