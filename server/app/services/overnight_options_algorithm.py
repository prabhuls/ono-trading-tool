"""
Overnight Options Algorithm Service

Implements the sophisticated multi-step algorithm to identify optimal call debit spreads
for SPY/SPX options during the critical 3:00-4:00 PM ET trading window.

Based on the requirements from PROJECT_REQUIREMENTS.md:
1. Filter strikes below current underlying price (in-the-money bias)
2. Calculate spreads with max cost filtering (default $0.74)
   - SPY: $1-wide spreads
   - SPX: $5-wide spreads (proportional to ~5x price scale)
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
    optimal call debit spreads for SPY ($1-wide) and SPX ($5-wide) options.
    """
    
    def __init__(self, max_cost_threshold: float = 0.74):
        """
        Initialize the algorithm with configurable parameters

        Args:
            max_cost_threshold: Maximum cost for spreads (default: $0.74 for SPY)
        """
        self.max_cost_threshold = max_cost_threshold
        self.max_cost_threshold_spy = 0.74
        self.max_cost_threshold_spx = 3.75
        self.thetradelist_service = get_thetradelist_service()
    
    async def get_current_price(self, ticker: str) -> float:
        """
        Get current underlying price from TheTradeList API
        
        Args:
            ticker: Underlying ticker symbol (e.g., "SPY", "SPX")
        
        Returns:
            Current underlying price as float
            
        Raises:
            ExternalAPIError: If unable to get underlying price
        """
        try:
            price_data = await self.thetradelist_service.get_stock_price(ticker)
            return float(price_data.get("price", 0))
        except Exception as e:
            logger.error("Failed to get underlying price for algorithm", ticker=ticker, error=str(e))
            raise ExternalAPIError(
                message=f"Failed to get {ticker} price: {str(e)}",
                service="overnight_options_algorithm"
            )
    
    def calculate_spread_cost(self, buy_option: Dict[str, Any], sell_option: Dict[str, Any], ticker: str = "SPY") -> float:
        """
        Calculate the cost of a spread using mid-market pricing

        SPY: $1-wide spreads, SPX: $5-wide spreads (scaled appropriately)
        Formula: spread_cost = buy_mid - sell_mid
        Where mid = (ask + bid) / 2 for each option

        Args:
            buy_option: Lower strike option to buy (more expensive)
            sell_option: Higher strike option to sell (less expensive)
            ticker: Underlying ticker for spread width determination

        Returns:
            Spread cost using mid-market pricing as float
        """
        try:
            # Calculate mid-market price for buy option (lower strike)
            buy_bid = float(buy_option.get("bid", 0))
            buy_ask = float(buy_option.get("ask", 0))
            buy_mid = (buy_ask + buy_bid) / 2

            # Calculate mid-market price for sell option (higher strike)
            sell_bid = float(sell_option.get("bid", 0))
            sell_ask = float(sell_option.get("ask", 0))
            sell_mid = (sell_ask + sell_bid) / 2

            # Calculate spread cost as difference between mid prices
            spread_cost = buy_mid - sell_mid

            # Could also check natural vs mid spread
            natural_cost = float(buy_option.get("ask", 0)) - float(sell_option.get("bid", 0))
            spread_width = abs(float(sell_option.get("strike", 0)) - float(buy_option.get("strike", 0)))

            # Reject if bid-ask too wide (>10% of spread width)
            if (natural_cost - spread_cost) > (spread_width * 0.10):
                return 0.0  # Too wide, reject

            # Ensure cost is not negative (which would be invalid for a debit spread)
            return max(0.0, spread_cost)

        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to calculate spread cost",
                buy_strike=buy_option.get("strike"),
                sell_strike=sell_option.get("strike"),
                error=str(e)
            )
            return 0.0
    
    def calculate_spread_metrics(self, spread_cost: float, ticker: str = "SPY") -> Dict[str, float]:
        """
        Calculate risk/reward metrics for a spread

        Args:
            spread_cost: Cost of the spread
            ticker: Underlying ticker for spread width determination

        Returns:
            Dictionary with max_reward, max_risk, roi_potential, profit_target
        """
        # Spread width: SPY uses $1, SPX uses $5
        max_value = 1.00 if ticker == "SPY" else 5.00
        max_reward = max_value - spread_cost
        max_risk = spread_cost
        roi_potential = (max_reward / spread_cost * 100) if spread_cost > 0 else 0

        # Apply ROI sanity check - max 200% (2:1 reward/risk)
        if roi_potential > 200:
            logger.warning(
                "ROI exceeds realistic threshold - likely pricing data issue",
                ticker=ticker,
                spread_cost=spread_cost,
                max_reward=max_reward,
                calculated_roi=roi_potential,
                max_allowed_roi=200
            )
            # Cap ROI at 200% for display purposes
            roi_potential = 200.0

        profit_target = spread_cost * 1.20  # 20% profit target

        # For SPX, round profit target to nearest 0.05
        if ticker == "SPX":
            profit_target = round(profit_target * 20) / 20  # Round to nearest 0.05

        return {
            "max_reward": round(max_reward, 2),
            "max_risk": round(max_risk, 2),
            "roi_potential": round(roi_potential, 1),
            "profit_target": round(profit_target, 2)
        }
    
    def filter_itm_strikes(self, contracts: List[Dict[str, Any]], current_price: float, ticker: str = "SPY") -> List[Dict[str, Any]]:
        """
        Filter strikes below current underlying price (in-the-money bias)
        
        For SPX, handles deep ITM scenarios where all available strikes are well below current price.
        In such cases, uses strikes closest to current price even if they're deep ITM.
        
        Args:
            contracts: List of option contracts
            current_price: Current underlying price
            ticker: Underlying ticker symbol
            
        Returns:
            Filtered list of contracts below current price (or closest available for SPX)
        """
        try:
            # Extract all strikes to analyze the range
            strikes = []
            for contract in contracts:
                strike = float(contract.get("strike", 0))
                if strike > 0:
                    strikes.append(strike)
            
            if not strikes:
                logger.warning("No valid strikes found in contracts", ticker=ticker)
                return []
            
            max_available_strike = max(strikes)
            min_available_strike = min(strikes)
            
            # Log strike analysis
            logger.info(
                "Strike analysis",
                ticker=ticker,
                current_price=current_price,
                max_available_strike=max_available_strike,
                min_available_strike=min_available_strike,
                gap_to_highest=(current_price - max_available_strike),
                total_strikes=len(strikes)
            )
            
            itm_contracts = []
            
            # For SPY: standard ITM filtering (strikes below current price)
            if ticker == "SPY":
                for contract in contracts:
                    strike = float(contract.get("strike", 0))
                    if strike < current_price:
                        itm_contracts.append(contract)
            
            # For SPX: Handle deep ITM scenarios
            else:  # SPX
                # Check if we're in deep ITM scenario (highest strike > 1000 points below current)
                if (current_price - max_available_strike) > 1000:
                    logger.info(
                        "SPX deep ITM scenario - using strikes closest to current price",
                        ticker=ticker,
                        current_price=current_price,
                        max_available_strike=max_available_strike,
                        gap=current_price - max_available_strike
                    )
                    
                    # Use the upper portion of available strikes (closest to current price)
                    # Take strikes that are within reasonable range of the highest available
                    threshold = max_available_strike - 500  # Use strikes within 500 points of the highest
                    
                    for contract in contracts:
                        strike = float(contract.get("strike", 0))
                        if strike >= threshold:  # Use strikes close to the highest available
                            itm_contracts.append(contract)
                
                else:
                    # Normal SPX filtering - strikes below current price
                    for contract in contracts:
                        strike = float(contract.get("strike", 0))
                        if strike < current_price:
                            itm_contracts.append(contract)
            
            # Log final results
            logger.info(
                "ITM contracts filtered",
                ticker=ticker,
                total_contracts=len(contracts),
                itm_contracts=len(itm_contracts),
                current_price=current_price,
                filtering_strategy="deep_itm" if (ticker == "SPX" and (current_price - max_available_strike) > 1000) else "standard_itm"
            )
            
            # Additional debug logging for strikes included
            if itm_contracts:
                included_strikes = [float(c.get("strike", 0)) for c in itm_contracts]
                logger.info(
                    "ITM strikes included",
                    ticker=ticker,
                    min_strike=min(included_strikes),
                    max_strike=max(included_strikes),
                    strike_count=len(included_strikes)
                )
            
            return itm_contracts
            
        except Exception as e:
            logger.error("Failed to filter ITM strikes", error=str(e))
            return []
    
    def find_qualifying_spreads(
        self,
        itm_contracts: List[Dict[str, Any]],
        ticker: str = "SPY",
        current_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all spreads that qualify based on cost threshold
        
        SPY: $1-wide spreads, SPX: $5-wide spreads
        
        Args:
            itm_contracts: List of ITM option contracts
            ticker: Underlying ticker symbol
            
        Returns:
            List of qualifying spreads with their metrics
        """
        qualifying_spreads = []
        
        # Sort contracts by strike price for easier pairing
        sorted_contracts = sorted(itm_contracts, key=lambda x: float(x.get("strike", 0)))
        
        # Determine spread width and max cost based on ticker
        spread_width = 1.0 if ticker == "SPY" else 5.0
        max_cost = self.max_cost_threshold_spy if ticker == "SPY" else self.max_cost_threshold_spx
        
        # Log detailed contract information
        contract_strikes = [float(c.get("strike", 0)) for c in sorted_contracts]
        logger.info(
            "Spread finding details",
            ticker=ticker,
            spread_width=spread_width,
            total_contracts=len(sorted_contracts),
            available_strikes=contract_strikes[:10] if len(contract_strikes) > 10 else contract_strikes,  # Log first 10 strikes
            max_cost_threshold=max_cost
        )
        
        spreads_attempted = 0
        spreads_with_missing_sell = 0
        spreads_with_invalid_cost = 0
        spreads_too_expensive = 0
        
        for i, buy_contract in enumerate(sorted_contracts):
            buy_strike = float(buy_contract.get("strike", 0))
            buy_ticker = buy_contract.get("contract_ticker", "")

            # Extract series type from contract ticker for SPX (SPX or SPXW)
            buy_series = ""
            if ticker == "SPX":
                if "SPX250" in buy_ticker and "SPXW" not in buy_ticker:
                    buy_series = "SPX"
                elif "SPXW250" in buy_ticker:
                    buy_series = "SPXW"

            # Find the sell contract (strike = buy_strike + spread_width)
            sell_strike = buy_strike + spread_width
            sell_contract = None

            # Collect all candidates with matching strike
            candidates = []
            for sell_candidate in sorted_contracts[i+1:]:
                if float(sell_candidate.get("strike", 0)) == sell_strike:
                    candidates.append(sell_candidate)

            # For SPX, prefer contracts from the same series
            if ticker == "SPX" and buy_series and len(candidates) > 1:
                # Try to find same series contract
                for candidate in candidates:
                    sell_ticker = candidate.get("contract_ticker", "")
                    if buy_series == "SPX" and "SPX250" in sell_ticker and "SPXW" not in sell_ticker:
                        sell_contract = candidate
                        break
                    elif buy_series == "SPXW" and "SPXW250" in sell_ticker:
                        sell_contract = candidate
                        break

            # If no same-series match or not SPX, take first candidate
            if not sell_contract and candidates:
                sell_contract = candidates[0]
            
            spreads_attempted += 1
            
            if not sell_contract:
                spreads_with_missing_sell += 1
                logger.debug(
                    "No matching sell contract found",
                    ticker=ticker,
                    buy_strike=buy_strike,
                    target_sell_strike=sell_strike,
                    spread_width=spread_width
                )
                continue  # No matching spread found
            
            # Calculate spread cost
            spread_cost = self.calculate_spread_cost(buy_contract, sell_contract, ticker)
            
            # Debug spread cost calculation
            logger.debug(
                "Spread cost calculated",
                ticker=ticker,
                buy_strike=buy_strike,
                sell_strike=sell_strike,
                spread_cost=spread_cost,
                buy_ask=buy_contract.get("ask", 0),
                sell_bid=sell_contract.get("bid", 0),
                max_threshold=max_cost
            )
            
            # Check if spread qualifies based on max cost threshold
            if spread_cost <= 0:
                spreads_with_invalid_cost += 1
                logger.debug(
                    "Invalid spread cost",
                    ticker=ticker,
                    buy_strike=buy_strike,
                    sell_strike=sell_strike,
                    spread_cost=spread_cost
                )
                continue
            elif spread_cost > max_cost:
                spreads_too_expensive += 1
                logger.debug(
                    "Spread too expensive",
                    ticker=ticker,
                    buy_strike=buy_strike,
                    sell_strike=sell_strike,
                    spread_cost=spread_cost,
                    threshold=max_cost
                )
                continue
            else:
                metrics = self.calculate_spread_metrics(spread_cost, ticker)
                
                spread_info = {
                    "buy_strike": buy_strike,
                    "sell_strike": sell_strike,
                    "buy_contract": buy_contract,
                    "sell_contract": sell_contract,
                    "buy_contract_ticker": buy_contract.get("contract_ticker"),  # Track specific contract
                    "sell_contract_ticker": sell_contract.get("contract_ticker"),  # Track specific contract
                    "spread_cost": round(spread_cost, 2),
                    "distance_from_current": abs(sell_strike - current_price) if current_price else 0,
                    **metrics
                }
                
                qualifying_spreads.append(spread_info)
                
                logger.debug(
                    "Qualifying spread found",
                    ticker=ticker,
                    buy_strike=buy_strike,
                    sell_strike=sell_strike,
                    spread_cost=spread_cost,
                    roi_potential=metrics.get("roi_potential", 0)
                )
        
        # Log comprehensive summary
        logger.info(
            "Qualifying spreads search completed",
            ticker=ticker,
            spread_width=spread_width,
            total_contracts=len(sorted_contracts),
            spreads_attempted=spreads_attempted,
            spreads_with_missing_sell=spreads_with_missing_sell,
            spreads_with_invalid_cost=spreads_with_invalid_cost,
            spreads_too_expensive=spreads_too_expensive,
            qualifying_spreads=len(qualifying_spreads),
            max_cost_threshold=max_cost
        )
        
        if qualifying_spreads:
            costs = [s["spread_cost"] for s in qualifying_spreads]
            logger.info(
                "Qualifying spread costs",
                ticker=ticker,
                min_cost=min(costs),
                max_cost=max(costs),
                avg_cost=round(sum(costs) / len(costs), 2)
            )
        
        return qualifying_spreads
    
    def select_optimal_spread(self, qualifying_spreads: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the optimal spread (deepest ITM for best risk management as per requirements)

        Args:
            qualifying_spreads: List of qualifying spreads

        Returns:
            Optimal spread (deepest ITM) or None if no spreads qualify
        """
        if not qualifying_spreads:
            return None

        # Always select deepest ITM (lowest sell strike) as per project requirements
        # This provides the best risk management and highest probability of success
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
            contract_ticker = contract.get("contract_ticker")
            highlighted_contract = contract.copy()

            # Default: no highlighting
            highlighted_contract["is_highlighted"] = None

            if optimal_spread:
                # Use specific contract tickers to highlight only the selected contracts
                buy_contract_ticker = optimal_spread.get("buy_contract_ticker")
                sell_contract_ticker = optimal_spread.get("sell_contract_ticker")

                # Match by contract ticker for precise highlighting
                if contract_ticker and contract_ticker == buy_contract_ticker:
                    highlighted_contract["is_highlighted"] = "buy"
                elif contract_ticker and contract_ticker == sell_contract_ticker:
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
            
            # Step 1: Get current underlying price
            current_price = await self.get_current_price(ticker)
            
            # Step 2: Get option chain with pricing
            option_chain_data = await self.thetradelist_service.build_option_chain_with_pricing(
                ticker=ticker,
                expiration_date=expiration_date
            )
            
            contracts = option_chain_data.get("contracts", [])
            if not contracts:
                logger.warning("No option contracts available for algorithm", ticker=ticker)
                return self._create_empty_result(ticker, expiration_date, current_price)
            
            # Step 3: Filter for ITM strikes (below current price)
            itm_contracts = self.filter_itm_strikes(contracts, current_price, ticker)
            
            # Step 4: Find qualifying spreads (width varies by ticker)
            qualifying_spreads = self.find_qualifying_spreads(itm_contracts, ticker, current_price)

            # Step 5: Select optimal spread (deepest ITM)
            optimal_spread = self.select_optimal_spread(qualifying_spreads)
            
            # Debug logging when no spreads found
            if not optimal_spread and len(qualifying_spreads) == 0:
                logger.warning(
                    "No spreads found - debugging info",
                    ticker=ticker,
                    total_contracts=len(contracts),
                    itm_contracts=len(itm_contracts),
                    current_price=current_price,
                    max_cost_threshold=self.max_cost_threshold,
                    spread_width=1.0 if ticker == "SPY" else 5.0
                )
            
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
                    "max_cost_threshold": self.max_cost_threshold_spy if ticker == "SPY" else self.max_cost_threshold_spx,
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
                    "target_roi": 20.0,  # Fixed 20% target per project requirements
                    "strategy": f"BUY {optimal_spread['buy_strike']:.0f} / SELL {optimal_spread['sell_strike']:.0f} CALL ({ticker})" if optimal_spread else None,
                    "expiration": option_chain_data.get("expiration_date"),
                    "qualified_spreads_count": len(qualifying_spreads)
                },
                "message": self._get_result_message(optimal_spread, len(qualifying_spreads), ticker)
            }
            
            logger.info(
                "Overnight options algorithm completed successfully",
                ticker=ticker,
                qualified_spreads=len(qualifying_spreads),
                optimal_spread_found=optimal_spread is not None,
                buy_strike=optimal_spread["buy_strike"] if optimal_spread else None,
                sell_strike=optimal_spread["sell_strike"] if optimal_spread else None,
                spread_cost=optimal_spread["spread_cost"] if optimal_spread else None,
                max_reward=optimal_spread["max_reward"] if optimal_spread else None,
                roi_potential=optimal_spread["roi_potential"] if optimal_spread else None
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
                "max_cost_threshold": self.max_cost_threshold_spy if ticker == "SPY" else self.max_cost_threshold_spx,
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
                "target_roi": 20.0,  # Fixed 20% target per project requirements
                "strategy": None,
                "expiration": expiration_date,
                "qualified_spreads_count": 0
            },
            "message": "No option contracts available for analysis"
        }
    
    def _get_result_message(self, optimal_spread: Optional[Dict[str, Any]], qualified_count: int, ticker: str = "SPY") -> str:
        """Get appropriate result message based on algorithm outcome"""
        spread_description = "$1-wide" if ticker == "SPY" else "$5-wide"
        
        if optimal_spread:
            return f"Optimal {spread_description} {ticker} spread: {optimal_spread['buy_strike']}/{optimal_spread['sell_strike']} at ${optimal_spread['spread_cost']} cost"
        elif qualified_count > 0:
            return f"Found {qualified_count} qualifying {spread_description} {ticker} spreads but no optimal selection made"
        else:
            return f"No qualifying {spread_description} {ticker} spreads found within cost threshold"


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