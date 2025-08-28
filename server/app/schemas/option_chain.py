from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class OptionContractData(BaseModel):
    """Individual option contract data"""
    
    strike: float = Field(..., description="Strike price of the option")
    bid: float = Field(..., description="Current bid price")
    ask: float = Field(..., description="Current ask price")
    volume: int = Field(..., description="Trading volume")
    openInterest: int = Field(..., alias="open_interest", description="Open interest")
    impliedVolatility: float = Field(..., alias="implied_volatility", description="Implied volatility")
    isHighlighted: Optional[Literal['buy', 'sell']] = Field(
        None, 
        alias="is_highlighted",
        description="Highlight type for the overnight algorithm (buy/sell/null)"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "strike": 580.0,
                "bid": 5.20,
                "ask": 5.25,
                "volume": 1250,
                "openInterest": 8500,
                "impliedVolatility": 0.185,
                "isHighlighted": "buy"
            }
        }


class OptionChainMetadata(BaseModel):
    """Option chain metadata"""
    
    ticker: str = Field(..., description="Underlying ticker symbol")
    expiration_date: str = Field(..., description="Option expiration date in YYYY-MM-DD format")
    current_price: float = Field(..., description="Current price of underlying asset")
    total_contracts: int = Field(..., description="Total number of contracts in chain")
    algorithm_applied: bool = Field(..., description="Whether overnight algorithm has been applied")
    max_cost_threshold: float = Field(..., description="Maximum cost threshold used for filtering")
    timestamp: str = Field(..., description="Timestamp when data was retrieved (ISO format with Z)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "SPY",
                "expiration_date": "2025-08-29",
                "current_price": 585.18,
                "total_contracts": 45,
                "algorithm_applied": True,
                "max_cost_threshold": 0.74,
                "timestamp": "2025-08-28T15:30:00Z"
            }
        }


class OptionChainResponse(BaseModel):
    """Complete option chain response with metadata"""
    
    success: bool = Field(..., description="Whether the request was successful")
    data: List[OptionContractData] = Field(..., description="List of option contracts")
    metadata: OptionChainMetadata = Field(..., description="Option chain metadata")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "strike": 580.0,
                        "bid": 5.20,
                        "ask": 5.25,
                        "volume": 1250,
                        "openInterest": 8500,
                        "impliedVolatility": 0.185,
                        "isHighlighted": "buy"
                    },
                    {
                        "strike": 581.0,
                        "bid": 4.30,
                        "ask": 4.35,
                        "volume": 980,
                        "openInterest": 6200,
                        "impliedVolatility": 0.178,
                        "isHighlighted": "sell"
                    }
                ],
                "metadata": {
                    "ticker": "SPY",
                    "expiration_date": "2025-08-29",
                    "current_price": 585.18,
                    "total_contracts": 45,
                    "algorithm_applied": True,
                    "max_cost_threshold": 0.74,
                    "timestamp": "2025-08-28T15:30:00Z"
                },
                "message": "Option chain retrieved successfully with overnight algorithm applied"
            }
        }


class AlgorithmResult(BaseModel):
    """Result from the overnight options algorithm"""
    
    selected_spread: Optional[dict] = Field(None, description="Selected optimal spread")
    buy_strike: Optional[float] = Field(None, description="Buy leg strike price")
    sell_strike: Optional[float] = Field(None, description="Sell leg strike price")
    spread_cost: Optional[float] = Field(None, description="Cost of the spread")
    max_reward: Optional[float] = Field(None, description="Maximum reward potential")
    max_risk: Optional[float] = Field(None, description="Maximum risk")
    roi_potential: Optional[float] = Field(None, description="ROI potential percentage")
    profit_target: Optional[float] = Field(None, description="20% profit target price")
    target_roi: float = Field(..., description="Fixed 20% profit target per project requirements")
    strategy: Optional[str] = Field(None, description="Formatted strategy string (e.g., 'BUY 580 / SELL 581 CALL')")
    expiration: Optional[str] = Field(None, description="Option expiration date in YYYY-MM-DD format")
    qualified_spreads_count: int = Field(..., description="Number of spreads that qualified")
    
    class Config:
        json_schema_extra = {
            "example": {
                "selected_spread": {
                    "buy_strike": 580.0,
                    "sell_strike": 581.0,
                    "cost": 0.73
                },
                "buy_strike": 580.0,
                "sell_strike": 581.0,
                "spread_cost": 0.73,
                "max_reward": 0.27,
                "max_risk": 0.73,
                "roi_potential": 37.0,
                "profit_target": 0.88,
                "target_roi": 20.0,
                "strategy": "BUY 580 / SELL 581 CALL",
                "expiration": "2025-08-29",
                "qualified_spreads_count": 3
            }
        }


class OptionChainWithAlgorithm(BaseModel):
    """Option chain response with algorithm results"""
    
    success: bool = Field(..., description="Whether the request was successful")
    data: List[OptionContractData] = Field(..., description="List of option contracts with highlights")
    metadata: OptionChainMetadata = Field(..., description="Option chain metadata")
    algorithm_result: AlgorithmResult = Field(..., description="Overnight algorithm results")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "strike": 580.0,
                        "bid": 5.20,
                        "ask": 5.25,
                        "volume": 1250,
                        "openInterest": 8500,
                        "impliedVolatility": 0.185,
                        "isHighlighted": "buy"
                    }
                ],
                "metadata": {
                    "ticker": "SPY",
                    "expiration_date": "2025-08-29",
                    "current_price": 585.18,
                    "total_contracts": 45,
                    "algorithm_applied": True,
                    "max_cost_threshold": 0.74,
                    "timestamp": "2025-08-28T15:30:00Z"
                },
                "algorithm_result": {
                    "buy_strike": 580.0,
                    "sell_strike": 581.0,
                    "spread_cost": 0.73,
                    "max_reward": 0.27,
                    "max_risk": 0.73,
                    "roi_potential": 37.0,
                    "profit_target": 0.88,
                    "target_roi": 20.0,
                    "strategy": "BUY 580 / SELL 581 CALL",
                    "expiration": "2025-08-29",
                    "qualified_spreads_count": 3
                },
                "message": "Option chain with overnight algorithm applied successfully"
            }
        }