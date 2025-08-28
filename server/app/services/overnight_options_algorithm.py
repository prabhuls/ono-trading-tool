"""
Overnight Options Algorithm Service

Implements the sophisticated multi-step algorithm to identify the optimal $1-wide call debit spread
for SPY options during the critical 3:20-3:40 PM ET trading window.

Based on the requirements from PROJECT_REQUIREMENTS.md:
1. Filter strikes below current SPY price (in-the-money bias)
2. Calculate $1-wide spreads with max cost filtering (default $0.74)
3. Select deepest ITM spread (lowest sell strike)
4. Mark BUY and SELL strikes with highlighting
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.core.logging import get_logger
from app.services.external.thetradelist_service import get_thetradelist_service
from app.services.external.base import ExternalAPIError


logger = get_logger(__name__)


class OvernightOptionsAlgorithm:
    """
    Overnight Options Algorithm implementation
    
    This service implements the overnight options trading algorithm that identifies
    optimal $1-wide call debit spreads for SPY options.
    """
    
    def __init__(self, max_cost_threshold: float = 0.74):
        """
        Initialize the algorithm with configurable parameters
        
        Args:
            max_cost_threshold: Maximum cost for spreads (default: $0.74)
        """
        self.max_cost_threshold = max_cost_threshold
        self.thetradelist_service = get_thetradelist_service()
    
    async def get_current_spy_price(self) -> float:
        """
        Get current SPY price from TheTradeList API
        
        Returns:
            Current SPY price as float
            
        Raises:
            ExternalAPIError: If unable to get SPY price
        """
        try:
            price_data = await self.thetradelist_service.get_stock_price("SPY")
            return float(price_data.get("price", 0))
        except Exception as e:
            logger.error("Failed to get SPY price for algorithm", error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get SPY price: {str(e)}",
                service="overnight_options_algorithm"
            )
    
    def calculate_spread_cost(self, buy_option: Dict[str, Any], sell_option: Dict[str, Any]) -> float:
        """
        Calculate the mid-price cost of a $1-wide call debit spread
        
        Formula: (Buy Ask - Sell Bid) / 2
        
        Args:
            buy_option: Lower strike option to buy (more expensive)
            sell_option: Higher strike option to sell (less expensive)
            
        Returns:
            Spread cost as float
        """
        try:
            buy_ask = float(buy_option.get("ask", 0))
            sell_bid = float(sell_option.get("bid", 0))
            
            # Mid-price calculation
            spread_cost = (buy_ask - sell_bid) / 2
            
            # Ensure cost is not negative
            return max(0.0, spread_cost)
            
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to calculate spread cost",
                buy_strike=buy_option.get("strike"),
                sell_strike=sell_option.get("strike"),
                error=str(e)
            )
            return 0.0
    
    def calculate_spread_metrics(self, spread_cost: float) -> Dict[str, float]:
        """
        Calculate risk/reward metrics for a spread
        
        Args:
            spread_cost: Cost of the spread
            
        Returns:
            Dictionary with max_reward, max_risk, roi_potential, profit_target
        """
        max_value = 1.00  # $1 spread width
        max_reward = max_value - spread_cost
        max_risk = spread_cost
        roi_potential = (max_reward / spread_cost * 100) if spread_cost > 0 else 0
        profit_target = spread_cost * 1.20  # 20% profit target
        
        return {
            "max_reward": round(max_reward, 2),
            "max_risk": round(max_risk, 2),
            "roi_potential": round(roi_potential, 1),
            "profit_target": round(profit_target, 2)
        }
    
    def filter_itm_strikes(self, contracts: List[Dict[str, Any]], current_price: float) -> List[Dict[str, Any]]:
        """
        Filter strikes below current SPY price (in-the-money bias)
        
        Args:
            contracts: List of option contracts
            current_price: Current SPY price
            
        Returns:
            Filtered list of contracts below current price
        """
        try:
            itm_contracts = []
            for contract in contracts:
                strike = float(contract.get("strike", 0))
                if strike < current_price:
                    itm_contracts.append(contract)
            
            logger.info(
                "ITM contracts filtered",
                total_contracts=len(contracts),
                itm_contracts=len(itm_contracts),
                current_price=current_price
            )
            
            return itm_contracts
            
        except Exception as e:
            logger.error("Failed to filter ITM strikes", error=str(e))
            return []
    
    def find_qualifying_spreads(
        self, 
        itm_contracts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find all $1-wide spreads that qualify based on cost threshold
        
        Args:
            itm_contracts: List of ITM option contracts
            
        Returns:
            List of qualifying spreads with their metrics
        """
        qualifying_spreads = []
        
        # Sort contracts by strike price for easier pairing
        sorted_contracts = sorted(itm_contracts, key=lambda x: float(x.get("strike", 0)))
        
        for i, buy_contract in enumerate(sorted_contracts):
            buy_strike = float(buy_contract.get("strike", 0))
            
            # Find the sell contract (strike = buy_strike + 1)
            sell_strike = buy_strike + 1
            sell_contract = None
            
            for sell_candidate in sorted_contracts[i+1:]:
                if float(sell_candidate.get("strike", 0)) == sell_strike:
                    sell_contract = sell_candidate
                    break
            
            if not sell_contract:
                continue  # No matching $1-wide spread found
            
            # Calculate spread cost
            spread_cost = self.calculate_spread_cost(buy_contract, sell_contract)
            
            # Check if spread qualifies based on max cost threshold
            if spread_cost <= self.max_cost_threshold and spread_cost > 0:
                metrics = self.calculate_spread_metrics(spread_cost)
                
                spread_info = {
                    "buy_strike": buy_strike,
                    "sell_strike": sell_strike,
                    "buy_contract": buy_contract,
                    "sell_contract": sell_contract,
                    "spread_cost": round(spread_cost, 2),
                    **metrics
                }
                
                qualifying_spreads.append(spread_info)
        
        logger.info(
            "Qualifying spreads found",
            total_spreads_checked=len(sorted_contracts),
            qualifying_spreads=len(qualifying_spreads),
            max_cost_threshold=self.max_cost_threshold
        )
        
        return qualifying_spreads
    
    def select_optimal_spread(self, qualifying_spreads: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the optimal spread (deepest ITM - lowest sell strike)
        
        Args:
            qualifying_spreads: List of qualifying spreads
            
        Returns:
            Optimal spread or None if no spreads qualify
        """
        if not qualifying_spreads:
            return None
        
        # Sort by sell_strike ascending to get deepest ITM spread
        optimal_spread = min(qualifying_spreads, key=lambda x: x["sell_strike"])
        
        logger.info(
            "Optimal spread selected",
            buy_strike=optimal_spread["buy_strike"],
            sell_strike=optimal_spread["sell_strike"],
            spread_cost=optimal_spread["spread_cost"],
            roi_potential=optimal_spread["roi_potential"]
        )
        
        return optimal_spread
    
    def apply_highlighting_to_contracts(
        self, 
        contracts: List[Dict[str, Any]], 
        optimal_spread: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply BUY/SELL highlighting to contracts based on optimal spread
        
        Args:
            contracts: List of option contracts
            optimal_spread: Selected optimal spread (or None)
            
        Returns:
            List of contracts with highlighting applied
        """
        highlighted_contracts = []
        
        for contract in contracts:
            strike = float(contract.get("strike", 0))
            highlighted_contract = contract.copy()
            
            # Default: no highlighting
            highlighted_contract["is_highlighted"] = None
            
            if optimal_spread:
                buy_strike = optimal_spread["buy_strike"]
                sell_strike = optimal_spread["sell_strike"]
                
                if strike == buy_strike:
                    highlighted_contract["is_highlighted"] = "buy"
                elif strike == sell_strike:
                    highlighted_contract["is_highlighted"] = "sell"
            
            highlighted_contracts.append(highlighted_contract)
        
        return highlighted_contracts
    
    async def run_algorithm(
        self, 
        ticker: str = "SPY",
        expiration_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete overnight options algorithm
        
        Args:
            ticker: Stock ticker (default: "SPY")
            expiration_date: Option expiration date (default: next trading day)
            
        Returns:
            Complete algorithm results with highlighted option chain and metrics
        """
        try:
            logger.info(
                "Starting overnight options algorithm",
                ticker=ticker,
                expiration_date=expiration_date,
                max_cost_threshold=self.max_cost_threshold
            )
            
            # Step 1: Get current SPY price
            current_price = await self.get_current_spy_price()
            
            # Step 2: Get option chain with pricing
            option_chain_data = await self.thetradelist_service.build_option_chain_with_pricing(
                ticker=ticker,
                expiration_date=expiration_date
            )
            
            contracts = option_chain_data.get("contracts", [])
            if not contracts:
                logger.warning("No option contracts available for algorithm")
                return self._create_empty_result(ticker, expiration_date, current_price)
            
            # Step 3: Filter for ITM strikes (below current price)
            itm_contracts = self.filter_itm_strikes(contracts, current_price)
            
            # Step 4: Find qualifying $1-wide spreads
            qualifying_spreads = self.find_qualifying_spreads(itm_contracts)
            
            # Step 5: Select optimal spread (deepest ITM)
            optimal_spread = self.select_optimal_spread(qualifying_spreads)
            
            # Step 6: Apply highlighting to all contracts
            highlighted_contracts = self.apply_highlighting_to_contracts(contracts, optimal_spread)
            
            # Build final result
            result = {
                "success": True,
                "data": highlighted_contracts,
                "metadata": {
                    "ticker": ticker,
                    "expiration_date": option_chain_data.get("expiration_date"),
                    "current_price": current_price,
                    "total_contracts": len(contracts),
                    "algorithm_applied": True,
                    "max_cost_threshold": self.max_cost_threshold,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "algorithm_result": {
                    "selected_spread": {
                        "buy_strike": optimal_spread["buy_strike"],
                        "sell_strike": optimal_spread["sell_strike"],
                        "cost": optimal_spread["spread_cost"]
                    } if optimal_spread else None,
                    "buy_strike": optimal_spread["buy_strike"] if optimal_spread else None,
                    "sell_strike": optimal_spread["sell_strike"] if optimal_spread else None,
                    "spread_cost": optimal_spread["spread_cost"] if optimal_spread else None,
                    "max_reward": optimal_spread["max_reward"] if optimal_spread else None,
                    "max_risk": optimal_spread["max_risk"] if optimal_spread else None,
                    "roi_potential": optimal_spread["roi_potential"] if optimal_spread else None,
                    "profit_target": optimal_spread["profit_target"] if optimal_spread else None,
                    "qualified_spreads_count": len(qualifying_spreads)
                },
                "message": self._get_result_message(optimal_spread, len(qualifying_spreads))
            }
            
            logger.info(
                "Overnight options algorithm completed successfully",
                ticker=ticker,
                qualified_spreads=len(qualifying_spreads),
                optimal_spread_found=optimal_spread is not None,
                buy_strike=optimal_spread["buy_strike"] if optimal_spread else None,
                sell_strike=optimal_spread["sell_strike"] if optimal_spread else None
            )
            
            return result
            
        except ExternalAPIError:
            raise
        except Exception as e:
            logger.error(
                "Overnight options algorithm failed",
                ticker=ticker,
                expiration_date=expiration_date,
                error=str(e)
            )
            raise ExternalAPIError(
                message=f"Algorithm failed for {ticker}: {str(e)}",
                service="overnight_options_algorithm"
            )
    
    def _create_empty_result(self, ticker: str, expiration_date: Optional[str], current_price: float) -> Dict[str, Any]:
        """Create empty result when no contracts are available"""
        return {
            "success": True,
            "data": [],
            "metadata": {
                "ticker": ticker,
                "expiration_date": expiration_date,
                "current_price": current_price,
                "total_contracts": 0,
                "algorithm_applied": True,
                "max_cost_threshold": self.max_cost_threshold,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "algorithm_result": {
                "selected_spread": None,
                "buy_strike": None,
                "sell_strike": None,
                "spread_cost": None,
                "max_reward": None,
                "max_risk": None,
                "roi_potential": None,
                "profit_target": None,
                "qualified_spreads_count": 0
            },
            "message": "No option contracts available for analysis"
        }
    
    def _get_result_message(self, optimal_spread: Optional[Dict[str, Any]], qualified_count: int) -> str:
        """Get appropriate result message based on algorithm outcome"""
        if optimal_spread:
            return f"Optimal spread identified: {optimal_spread['buy_strike']}/{optimal_spread['sell_strike']} at ${optimal_spread['spread_cost']} cost"
        elif qualified_count > 0:
            return f"Found {qualified_count} qualifying spreads but no optimal selection made"
        else:
            return "No qualifying spreads found within cost threshold"


# Singleton pattern
_overnight_options_algorithm: Optional[OvernightOptionsAlgorithm] = None


def get_overnight_options_algorithm(max_cost_threshold: float = 0.74) -> OvernightOptionsAlgorithm:
    """
    Get singleton OvernightOptionsAlgorithm instance
    
    Args:
        max_cost_threshold: Maximum cost threshold for spreads
        
    Returns:
        OvernightOptionsAlgorithm instance
    """
    global _overnight_options_algorithm
    if _overnight_options_algorithm is None or _overnight_options_algorithm.max_cost_threshold != max_cost_threshold:
        _overnight_options_algorithm = OvernightOptionsAlgorithm(max_cost_threshold)
    return _overnight_options_algorithm