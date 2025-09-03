"""
Calculations for TradeList data processing
"""
from typing import List, Dict, Optional
import statistics
import math
from datetime import datetime, timedelta


class VariabilityCalculator:
    """Calculate variability and other metrics for stock data"""
    
    @staticmethod
    def calculate_variability(price_history: List[float]) -> float:
        """
        Calculate price variability as coefficient of variation
        
        Args:
            price_history: List of historical prices
            
        Returns:
            Variability score (0-100)
        """
        if not price_history or len(price_history) < 2:
            return 0.0
        
        try:
            mean_price = statistics.mean(price_history)
            if mean_price == 0:
                return 0.0
            
            std_dev = statistics.stdev(price_history)
            cv = (std_dev / mean_price) * 100
            
            # Cap at 100 for extreme cases
            return min(cv, 100.0)
        except:
            return 0.0
    
    @staticmethod
    def calculate_average_move(price_history: List[float]) -> float:
        """
        Calculate average daily price movement percentage
        
        Args:
            price_history: List of historical prices
            
        Returns:
            Average daily move percentage
        """
        if not price_history or len(price_history) < 2:
            return 0.0
        
        daily_moves = []
        for i in range(1, len(price_history)):
            if price_history[i-1] != 0:
                move = abs((price_history[i] - price_history[i-1]) / price_history[i-1]) * 100
                daily_moves.append(move)
        
        return statistics.mean(daily_moves) if daily_moves else 0.0
    
    @staticmethod
    def calculate_trend_strength(prices: List[float], window: int = 20) -> float:
        """
        Calculate trend strength using linear regression slope
        
        Args:
            prices: List of prices
            window: Number of periods to consider
            
        Returns:
            Trend strength (-100 to 100)
        """
        if not prices or len(prices) < 2:
            return 0.0
        
        # Use last 'window' prices
        recent_prices = prices[-window:] if len(prices) >= window else prices
        n = len(recent_prices)
        
        if n < 2:
            return 0.0
        
        # Calculate linear regression slope
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(recent_prices) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, recent_prices))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # Normalize slope to -100 to 100 based on price range
        price_range = max(recent_prices) - min(recent_prices)
        if price_range > 0:
            normalized_slope = (slope / price_range) * 100
            return max(-100, min(100, normalized_slope))
        
        return 0.0
    
    @staticmethod
    def calculate_momentum(prices: List[float], period: int = 10) -> float:
        """
        Calculate price momentum
        
        Args:
            prices: List of prices
            period: Lookback period
            
        Returns:
            Momentum percentage
        """
        if not prices or len(prices) <= period:
            return 0.0
        
        current_price = prices[-1]
        past_price = prices[-period-1]
        
        if past_price == 0:
            return 0.0
        
        return ((current_price - past_price) / past_price) * 100
    
    @staticmethod
    def calculate_volatility_percentile(current_vol: float, historical_vols: List[float]) -> float:
        """
        Calculate where current volatility stands relative to historical
        
        Args:
            current_vol: Current volatility
            historical_vols: List of historical volatilities
            
        Returns:
            Percentile (0-100)
        """
        if not historical_vols:
            return 50.0
        
        count_below = sum(1 for vol in historical_vols if vol < current_vol)
        return (count_below / len(historical_vols)) * 100


class OptionMetricsCalculator:
    """Calculate option-specific metrics"""
    
    @staticmethod
    def calculate_true_roi(net_credit: float, max_risk: float) -> float:
        """
        Calculate true ROI for credit spreads
        
        Args:
            net_credit: Net credit received
            max_risk: Maximum risk (collateral)
            
        Returns:
            ROI percentage
        """
        if max_risk <= 0:
            return 0.0
        
        return (net_credit / max_risk) * 100
    
    @staticmethod
    def calculate_breakeven(strike: float, premium: float, option_type: str) -> float:
        """
        Calculate breakeven price for an option
        
        Args:
            strike: Strike price
            premium: Option premium
            option_type: 'call' or 'put'
            
        Returns:
            Breakeven price
        """
        if option_type.lower() == 'call':
            return strike + premium
        elif option_type.lower() == 'put':
            return strike - premium
        else:
            return strike
    
    @staticmethod
    def calculate_pop(current_price: float, strike: float, iv: float, dte: int, option_type: str) -> float:
        """
        Calculate probability of profit (simplified)
        
        Args:
            current_price: Current stock price
            strike: Strike price
            iv: Implied volatility (as decimal)
            dte: Days to expiration
            option_type: 'call' or 'put'
            
        Returns:
            Probability of profit (0-100)
        """
        if dte <= 0 or iv <= 0:
            return 50.0
        
        # Simplified calculation using distance from strike
        # More accurate would use Black-Scholes
        daily_vol = iv / (365 ** 0.5)
        expected_move = daily_vol * (dte ** 0.5) * current_price
        
        if option_type.lower() == 'put':
            distance = current_price - strike
        else:
            distance = strike - current_price
        
        if expected_move == 0:
            return 50.0
        
        # Convert to z-score and approximate probability
        z_score = distance / expected_move
        
        # Simplified normal CDF approximation
        if z_score > 3:
            return 99.0
        elif z_score < -3:
            return 1.0
        else:
            # Linear approximation for simplicity
            prob = 50 + (z_score * 16.67)
            return max(1, min(99, prob))
    
    @staticmethod
    def calculate_safety_score(
        current_price: float,
        strike: float,
        iv_rank: float,
        dte: int,
        option_type: str
    ) -> float:
        """
        Calculate safety score for an option position
        
        Args:
            current_price: Current stock price
            strike: Strike price
            iv_rank: IV rank (0-100)
            dte: Days to expiration
            option_type: 'call' or 'put'
            
        Returns:
            Safety score (0-100)
        """
        score = 0.0
        
        # Distance from strike (max 40 points)
        if option_type.lower() == 'put':
            distance_pct = ((current_price - strike) / current_price) * 100
        else:
            distance_pct = ((strike - current_price) / current_price) * 100
        
        if distance_pct > 10:
            score += 40
        elif distance_pct > 5:
            score += 30
        elif distance_pct > 3:
            score += 20
        elif distance_pct > 0:
            score += 10
        
        # IV rank component (max 30 points)
        if iv_rank > 50:
            score += 30
        elif iv_rank > 30:
            score += 20
        elif iv_rank > 20:
            score += 10
        
        # DTE component (max 30 points)
        if 20 <= dte <= 45:
            score += 30
        elif 15 <= dte <= 60:
            score += 20
        elif 10 <= dte <= 90:
            score += 10
        
        return min(100, score)


class BlackScholesCalculator:
    """Black-Scholes option pricing and implied volatility calculations"""
    
    @staticmethod
    def normal_cdf(x: float) -> float:
        """
        Cumulative distribution function for standard normal distribution
        Using Abramowitz and Stegun approximation
        """
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    @staticmethod
    def black_scholes_call_price(
        S: float,  # Current stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (in years)
        r: float,  # Risk-free rate
        sigma: float  # Volatility
    ) -> float:
        """
        Calculate theoretical call option price using Black-Scholes formula
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration in years
            r: Risk-free rate (annualized)
            sigma: Implied volatility (annualized)
            
        Returns:
            Theoretical option price
        """
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
            
        try:
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            call_price = S * BlackScholesCalculator.normal_cdf(d1) - K * math.exp(-r * T) * BlackScholesCalculator.normal_cdf(d2)
            return max(0.0, call_price)
        except:
            return 0.0
    
    @staticmethod
    def approximate_implied_volatility(
        market_price: float,  # Current market price of option
        S: float,  # Current stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (in years)
        r: float = 0.05  # Risk-free rate (default 5%)
    ) -> Optional[float]:
        """
        Approximate implied volatility using Newton-Raphson method
        
        Args:
            market_price: Current market price of the option (bid/ask midpoint)
            S: Current stock price
            K: Strike price
            T: Time to expiration in years
            r: Risk-free rate (default 5%)
            
        Returns:
            Implied volatility or None if calculation fails
        """
        if market_price <= 0 or S <= 0 or K <= 0 or T <= 0:
            return None
            
        # Initial guess for volatility (20%)
        sigma = 0.20
        
        # Newton-Raphson parameters
        max_iterations = 100
        tolerance = 1e-6
        
        try:
            for i in range(max_iterations):
                # Calculate theoretical price and vega (derivative with respect to sigma)
                d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                
                theoretical_price = BlackScholesCalculator.black_scholes_call_price(S, K, T, r, sigma)
                
                # Calculate vega (sensitivity to volatility)
                vega = S * math.sqrt(T) * BlackScholesCalculator.normal_cdf(d1) / math.sqrt(2 * math.pi) * math.exp(-0.5 * d1**2)
                
                if abs(vega) < 1e-10:  # Avoid division by zero
                    break
                
                # Newton-Raphson update
                price_diff = theoretical_price - market_price
                
                if abs(price_diff) < tolerance:
                    break
                    
                sigma_new = sigma - price_diff / vega
                
                # Keep sigma in reasonable bounds
                sigma_new = max(0.01, min(5.0, sigma_new))
                
                if abs(sigma_new - sigma) < tolerance:
                    break
                    
                sigma = sigma_new
            
            # Sanity check: return only reasonable IV values
            if 0.05 <= sigma <= 3.0:  # Between 5% and 300%
                return sigma
            else:
                return None
                
        except Exception:
            return None
    
    @staticmethod
    def calculate_time_to_expiration(expiration_date: str) -> float:
        """
        Calculate time to expiration in years
        
        Args:
            expiration_date: Expiration date in YYYY-MM-DD format
            
        Returns:
            Time to expiration in years
        """
        try:
            exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
            current_date = datetime.now()
            
            days_to_expiry = (exp_date - current_date).days
            
            # Convert to years (using 252 trading days per year)
            return max(0.0, days_to_expiry / 365.0)
        except:
            return 0.0