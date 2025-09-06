"""
Credit Spread Scanner Service
Analyzes credit spreads based on trend direction with safety-first approach
Uses natural pricing (bid-ask execution) for conservative risk assessment
Implements exact logic from CashFlowAgent-Scanner-1
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from app.services.tradelist.client import TradeListClient

logger = logging.getLogger(__name__)


class CreditSpreadScanner:
    """Handles trend-based credit spread detection with natural pricing (conservative approach)"""
    
    def __init__(self):
        self.tradelist_client = TradeListClient()
        self.api_call_count = 0
        self.max_api_calls = 2000
        self.session_quote_cache = {}  # Session-level cache
    
    async def find_best_credit_spread(
        self, 
        symbol: str, 
        current_price: float, 
        trend: str
    ) -> Dict:
        """Main function to find best credit spread based on trend direction"""
        try:
            self.api_call_count = 0
            self.session_quote_cache.clear()
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
            # - Uptrend = Put credit spreads (sell puts below current price)
            # - Downtrend = Call credit spreads (sell calls above current price)
            option_type = 'put' if trend == 'uptrend' else 'call'
            filtered_contracts = [
                c for c in closest_expiration_contracts 
                if c.get('contract_type', '').lower() == option_type
            ]
            
            if not filtered_contracts:
                return {
                    'found': False, 
                    'reason': f'No {option_type} contracts found for closest expiration'
                }
            
            # Step 4: Apply trend-based strike filtering
            valid_strikes = self.filter_strikes_by_trend(
                filtered_contracts, 
                current_price, 
                trend
            )
            if len(valid_strikes) < 2:
                return {
                    'found': False, 
                    'reason': f'Insufficient {option_type} strikes for {trend} credit spread'
                }
            
            # Step 5: Generate and test spread combinations
            best_spread = await self.test_credit_spread_combinations(
                valid_strikes, 
                current_price, 
                trend, 
                option_type
            )
            
            if best_spread:
                logger.info(f"Found {trend} credit spread: {best_spread['roi_percent']:.1f}% ROI")
                # Add price scenarios
                scenarios = self.calculate_price_scenarios(
                    best_spread, 
                    current_price, 
                    trend
                )
                best_spread['price_scenarios'] = scenarios
                return best_spread
            else:
                return {
                    'found': False, 
                    'reason': f'No {trend} credit spreads found within 7-15% ROI range'
                }
                
        except Exception as e:
            logger.error(f"Error in credit spread analysis: {str(e)}")
            return {'found': False, 'reason': f'Analysis error: {str(e)}'}
    
    async def get_all_contracts(self, symbol: str) -> List[Dict]:
        """Fetch all option contracts for a symbol"""
        try:
            contracts = await self.tradelist_client.get_options_contracts(symbol, limit=1000)
            logger.info(f"Retrieved {len(contracts)} contracts for {symbol}")
            return contracts
        except Exception as e:
            logger.error(f"Error fetching contracts: {e}")
            return []
    
    def filter_to_closest_expiration(self, contracts: List[Dict]) -> List[Dict]:
        """Filter contracts to closest expiration with minimum 3 DTE"""
        try:
            current_date = datetime.now().date()
            min_expiration = current_date + timedelta(days=3)
            
            # Get all unique expiration dates
            expirations = set()
            for contract in contracts:
                exp_str = contract.get('expiration_date', '')
                if exp_str:
                    try:
                        exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                        if exp_date >= min_expiration:
                            expirations.add(exp_date)
                    except:
                        continue
            
            if not expirations:
                logger.error("No valid expirations found (minimum 3 DTE)")
                return []
            
            # Select closest valid expiration
            closest_expiration = min(expirations)
            closest_exp_str = closest_expiration.strftime('%Y-%m-%d')
            
            # Filter contracts to this expiration only
            filtered_contracts = [
                c for c in contracts 
                if c.get('expiration_date') == closest_exp_str
            ]
            
            dte = (closest_expiration - current_date).days
            logger.info(
                f"Selected closest expiration: {closest_exp_str} "
                f"({dte} DTE) with {len(filtered_contracts)} contracts"
            )
            
            return filtered_contracts
            
        except Exception as e:
            logger.error(f"Error filtering expiration dates: {str(e)}")
            return []
    
    def filter_strikes_by_trend(
        self, 
        contracts: List[Dict], 
        current_price: float, 
        trend: str
    ) -> List[Dict]:
        """Filter strikes based on trend direction for maximum safety"""
        try:
            # Filter for realistic strikes near current price first
            realistic_contracts = []
            for c in contracts:
                strike = float(c.get('strike_price', 0))
                # Only use strikes within 85%-115% of current price
                if current_price * 0.85 <= strike <= current_price * 1.15:
                    realistic_contracts.append(c)
            
            logger.info(
                f"Filtered to {len(realistic_contracts)} realistic contracts "
                f"(85%-115% of current price)"
            )
            
            if trend == 'uptrend':
                # Uptrend: Put credit spreads - use strikes below 95% of current price
                safety_threshold = current_price * 0.95
                valid_contracts = [
                    c for c in realistic_contracts 
                    if float(c.get('strike_price', 0)) < safety_threshold
                ]
                logger.info(
                    f"Uptrend: Using put strikes below ${safety_threshold:.2f} "
                    f"(95% of current)"
                )
            else:
                # Downtrend: Call credit spreads - use strikes above 105% of current price
                safety_threshold = current_price * 1.05
                valid_contracts = [
                    c for c in realistic_contracts 
                    if float(c.get('strike_price', 0)) > safety_threshold
                ]
                logger.info(
                    f"Downtrend: Using call strikes above ${safety_threshold:.2f} "
                    f"(105% of current)"
                )
            
            # Sort by strike price for systematic combination testing
            valid_contracts.sort(key=lambda x: float(x.get('strike_price', 0)))
            
            logger.info(f"Found {len(valid_contracts)} valid strikes for {trend} credit spread")
            return valid_contracts
            
        except Exception as e:
            logger.error(f"Error filtering strikes by trend: {str(e)}")
            return []
    
    async def test_credit_spread_combinations(
        self, 
        contracts: List[Dict], 
        current_price: float, 
        trend: str, 
        option_type: str
    ) -> Optional[Dict]:
        """Test all credit spread combinations using parallel processing"""
        try:
            # Generate all possible strike pairs based on trend direction
            strike_pairs = []
            if trend == 'uptrend':
                # Put credit: SELL higher strike, BUY lower strike
                for i in range(len(contracts)):
                    for j in range(i+1, len(contracts)):
                        sell_contract = contracts[j]  # SELL higher strike put
                        buy_contract = contracts[i]   # BUY lower strike put
                        strike_pairs.append((sell_contract, buy_contract))
            else:
                # Call credit: SELL lower strike, BUY higher strike
                for i in range(len(contracts)):
                    for j in range(i+1, len(contracts)):
                        sell_contract = contracts[i]  # SELL lower strike call
                        buy_contract = contracts[j]   # BUY higher strike call
                        strike_pairs.append((sell_contract, buy_contract))
            
            total_combinations = len(strike_pairs)
            logger.info(f"Testing {total_combinations} combinations")
            
            # Sort pairs by distance from current price (furthest first for safety)
            if trend == 'uptrend':
                strike_pairs.sort(
                    key=lambda x: current_price - float(x[0]['strike_price']), 
                    reverse=True
                )
            else:
                strike_pairs.sort(
                    key=lambda x: float(x[0]['strike_price']) - current_price, 
                    reverse=True
                )
            
            # Process combinations in batches for parallel execution
            batch_size = 10  # Process 10 combinations at a time
            valid_spreads = []
            
            for batch_start in range(0, len(strike_pairs), batch_size):
                batch_end = min(batch_start + batch_size, len(strike_pairs))
                batch_pairs = strike_pairs[batch_start:batch_end]
                
                # Create tasks for parallel execution
                tasks = [
                    self.calculate_credit_spread_metrics(
                        sell_contract, 
                        buy_contract, 
                        current_price, 
                        trend, 
                        option_type
                    )
                    for sell_contract, buy_contract in batch_pairs
                ]
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for spread in batch_results:
                    if isinstance(spread, Exception):
                        logger.warning(f"Error calculating spread: {spread}")
                        continue
                    
                    if spread and spread.get('valid'):
                        roi = spread.get('roi_percent', 0)
                        # Target 7-15% ROI
                        if 7 <= roi <= 15:
                            valid_spreads.append(spread)
                            logger.info(
                                f"Valid spread found: {roi:.1f}% ROI "
                                f"(SELL ${spread['sell_strike']} / BUY ${spread['buy_strike']})"
                            )
                
                # Early exit if we found enough valid spreads
                if len(valid_spreads) >= 5:
                    logger.info(f"Found {len(valid_spreads)} valid spreads, stopping search")
                    break
            
            # Select best spread using weighted safety scoring
            if valid_spreads:
                best_spread = self.select_best_spread_by_safety(
                    valid_spreads, 
                    current_price, 
                    trend
                )
                return best_spread
            
            return None
            
        except Exception as e:
            logger.error(f"Error in credit spread combinations: {str(e)}")
            return None
    
    async def calculate_credit_spread_metrics(
        self, 
        sell_contract: Dict, 
        buy_contract: Dict, 
        current_price: float, 
        trend: str, 
        option_type: str
    ) -> Optional[Dict]:
        """Calculate credit spread metrics using natural pricing (conservative approach)"""
        try:
            sell_strike = float(sell_contract['strike_price'])
            buy_strike = float(buy_contract['strike_price'])
            
            # Get quotes with session-level caching
            sell_quote = await self.get_cached_quote(sell_contract['ticker'])
            if not sell_quote:
                return None
            
            buy_quote = await self.get_cached_quote(buy_contract['ticker'])
            if not buy_quote:
                return None
            
            # Extract bid/ask prices
            sell_bid = float(sell_quote.get('bid_price', 0))
            sell_ask = float(sell_quote.get('ask_price', 0))
            buy_bid = float(buy_quote.get('bid_price', 0))
            buy_ask = float(buy_quote.get('ask_price', 0))
            
            # Validate quotes
            if sell_bid <= 0 or sell_ask <= 0 or buy_bid <= 0 or buy_ask <= 0:
                return None
            
            # Calculate spread width for bid-ask validation
            spread_width = abs(sell_strike - buy_strike)
            
            # Validate bid-ask spreads aren't too wide (reject if > 10% of spread width)
            sell_spread_pct = (sell_ask - sell_bid) / spread_width * 100 if spread_width > 0 else 0
            buy_spread_pct = (buy_ask - buy_bid) / spread_width * 100 if spread_width > 0 else 0
            
            if sell_spread_pct > 10 or buy_spread_pct > 10:
                return None
            
            # Calculate using natural pricing (conservative execution cost)
            # Credit spread: sell_bid - buy_ask (actual credit received)
            net_credit = sell_bid - buy_ask
            
            # Maximum $10 spread width
            if spread_width > 10:
                return None
            
            max_risk = spread_width - net_credit
            
            if net_credit <= 0 or max_risk <= 0:
                return None
            
            # True ROI calculation
            roi_percent = (net_credit / max_risk) * 100
            
            # Calculate breakeven and safety margin
            if option_type == 'call':
                breakeven = sell_strike + net_credit
                safety_margin = ((sell_strike - current_price) / current_price) * 100
                margin_direction = "above current price"
            else:
                breakeven = sell_strike - net_credit
                safety_margin = ((current_price - sell_strike) / current_price) * 100
                margin_direction = "below current price"
            
            # Calculate DTE
            exp_date = datetime.strptime(sell_contract['expiration_date'], '%Y-%m-%d')
            dte = (exp_date - datetime.now()).days
            
            return {
                'found': True,
                'valid': True,
                'spread_type': f'{option_type}_credit',
                'trend': trend,
                'expiration': sell_contract['expiration_date'],
                'dte': dte,
                'sell_strike': sell_strike,
                'buy_strike': buy_strike,
                'net_credit': round(net_credit, 2),
                'max_risk': round(max_risk, 2),
                'max_profit': round(net_credit, 2),
                'roi_percent': round(roi_percent, 1),
                'breakeven': round(breakeven, 2),
                'safety_margin': f"{abs(safety_margin):.1f}% {margin_direction}",
                'sell_contract': sell_contract['ticker'],
                'buy_contract': buy_contract['ticker'],
                'quote_calls_used': self.api_call_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating spread metrics: {str(e)}")
            return None
    
    def select_best_spread_by_safety(
        self, 
        spreads: List[Dict], 
        current_price: float, 
        trend: str
    ) -> Dict:
        """Select best spread using weighted safety scoring system"""
        
        def calculate_safety_score(spread):
            """Calculate weighted safety score: Distance (50%) + Risk (30%) + ROI (20%)"""
            
            # Distance Factor (50% weight)
            if trend == "uptrend":
                distance_ratio = (current_price - spread['sell_strike']) / current_price
            else:
                distance_ratio = (spread['sell_strike'] - current_price) / current_price
            
            distance_score = max(0, distance_ratio) * 0.50
            
            # Risk Factor (30% weight)
            max_risk = spread['max_risk']
            risk_score = (1 / max_risk) * 0.30 if max_risk > 0 else 0
            
            # ROI Factor (20% weight)
            roi_score = (spread['roi_percent'] / 15.0) * 0.20
            
            total_score = distance_score + risk_score + roi_score
            
            return {
                'total_score': total_score,
                'distance_score': distance_score,
                'risk_score': risk_score,
                'roi_score': roi_score,
                'distance_ratio': distance_ratio * 100
            }
        
        # Calculate safety scores for all spreads
        scored_spreads = []
        for spread in spreads:
            scores = calculate_safety_score(spread)
            spread['safety_scores'] = scores
            scored_spreads.append(spread)
        
        # Select spread with highest safety score
        best_spread = max(scored_spreads, key=lambda x: x['safety_scores']['total_score'])
        
        logger.info(
            f"Selected best spread with safety score: "
            f"{best_spread['safety_scores']['total_score']:.4f}"
        )
        
        return best_spread
    
    def calculate_price_scenarios(
        self, 
        spread_data: Dict, 
        current_price: float, 
        trend: str
    ) -> Dict:
        """Calculate price scenarios for credit spread"""
        scenarios = {}
        price_levels = [-10, -5, -2.5, -1, 0, 1, 2.5, 5, 10]  # Percentage changes
        
        sell_strike = spread_data['sell_strike']
        buy_strike = spread_data['buy_strike']
        net_credit = spread_data['net_credit']
        max_risk = spread_data['max_risk']
        option_type = spread_data['spread_type'].replace('_credit', '')
        
        for pct_change in price_levels:
            future_price = current_price * (1 + pct_change / 100)
            
            # Calculate option values at expiration
            if option_type == 'call':
                sell_value = max(0, future_price - sell_strike)
                buy_value = max(0, future_price - buy_strike)
            else:  # put
                sell_value = max(0, sell_strike - future_price)
                buy_value = max(0, buy_strike - future_price)
            
            # Credit spread P&L
            spread_cost_at_expiration = buy_value - sell_value
            profit_loss = net_credit - spread_cost_at_expiration
            
            scenarios[f"{pct_change:+g}%"] = {
                'stock_price': round(future_price, 2),
                'sell_option_value': round(sell_value, 2),
                'buy_option_value': round(buy_value, 2),
                'spread_cost': round(spread_cost_at_expiration, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_percent': round((profit_loss / max_risk) * 100, 1) if max_risk > 0 else 0
            }
        
        return {
            'price_scenarios': scenarios,
            'max_profit_details': {
                'max_profit': round(net_credit, 2),
                'occurs_when': 'Both options expire worthless (optimal outcome)',
                'probability': 'High due to safety-first strike selection'
            },
            'risk_assessment': {
                'max_risk': round(max_risk, 2),
                'risk_description': self.get_risk_description(trend, option_type),
                'management': 'Monitor for early assignment signals'
            }
        }
    
    def get_risk_description(self, trend: str, option_type: str) -> str:
        """Get risk description based on trend and option type"""
        if trend == 'uptrend' and option_type == 'put':
            return 'Low Risk - Put strikes below current price in uptrend'
        elif trend == 'downtrend' and option_type == 'call':
            return 'Low Risk - Call strikes above current price in downtrend'
        else:
            return 'Moderate Risk - Monitor trend continuation'
    
    def calculate_dte(self, expiration_date: str) -> int:
        """Calculate days to expiration"""
        try:
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            return (exp_date - datetime.now()).days
        except:
            return 0
    
    async def get_cached_quote(self, contract_ticker: str) -> Optional[Dict]:
        """Get quote with session-level caching to reduce API calls"""
        # Check if quote is already cached for this session
        if contract_ticker in self.session_quote_cache:
            logger.debug(f"Using cached quote for {contract_ticker}")
            return self.session_quote_cache[contract_ticker]
        
        # Fetch fresh quote and cache it
        logger.debug(f"Fetching fresh quote for {contract_ticker}")
        quote = await self.tradelist_client.get_option_quote(contract_ticker)
        
        if quote:
            self.session_quote_cache[contract_ticker] = quote
            self.api_call_count += 1
            logger.debug(f"Cached quote for {contract_ticker}, total API calls: {self.api_call_count}")
        else:
            logger.warning(f"Failed to get quote for {contract_ticker}")
        
        return quote