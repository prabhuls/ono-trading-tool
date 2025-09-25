"""
Market Data API Endpoints
Provides market movers and stock data
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movers import TodaysMover
from app.core.database import get_async_session
from app.core.auth import conditional_jwt_token
from app.core.security import JWTPayload

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/todays-movers")
async def get_todays_movers(
    limit: int = 5,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Get today's market movers with verified credit spreads
    Returns top movers that have viable credit spread opportunities
    """
    try:
        logger.info('Fetching today\'s market movers with verified credit spreads...')
        
        # Query for movers that have spreads available AND no upcoming earnings
        # This filters out stocks with earnings risk
        result = await session.execute(
            select(TodaysMover)
            .where(
                and_(
                    TodaysMover.has_spreads == True,
                    TodaysMover.upcoming_earnings != True  # Exclude stocks with upcoming earnings
                )
            )
            .order_by(desc(TodaysMover.volume))
            .limit(limit)
        )
        
        movers = result.scalars().all()
        
        # Transform to match frontend expectations
        transformed_stocks = []
        for mover in movers:
            transformed_stocks.append({
                'id': mover.id,
                'symbol': mover.symbol,
                'name': mover.name or mover.symbol,  # Use name if available, else symbol
                'moverType': mover.mover_type,
                'currentPrice': float(mover.current_price) if mover.current_price else 0,
                'priceChange': float(mover.price_change) if mover.price_change else 0,
                'priceChangePercent': float(mover.price_change_percent) if mover.price_change_percent else 0,
                'volume': mover.volume,
                'specialCharacter': mover.special_character,
                'lastUpdated': mover.last_updated.isoformat() if mover.last_updated else None,
                'calculatedAt': mover.calculated_at.isoformat() if mover.calculated_at else None,
                'hasEarnings': mover.upcoming_earnings,
                'hasWeeklies': mover.has_weeklies,
                'hasSpreads': mover.has_spreads
            })
        
        logger.info(f'Found {len(transformed_stocks)} movers from database')
        
        return {
            'stocks': transformed_stocks,
            'timestamp': datetime.utcnow().isoformat()
        }
            
    except Exception as e:
        logger.error(f'Error fetching today\'s movers: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to fetch market movers'
        )


@router.get("/stock/{symbol}")
async def get_stock_data(
    symbol: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[JWTPayload] = Depends(conditional_jwt_token)
):
    """
    Get detailed stock data for a specific symbol
    """
    try:
        symbol = symbol.upper()
        
        # Query stock data from database
        from app.models.stocks import Stock
        
        result = await session.execute(
            select(Stock)
            .where(Stock.symbol == symbol)
        )
        
        stock = result.scalar_one_or_none()
        
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f'Stock {symbol} not found'
            )
        
        return {
            'symbol': stock.symbol,
            'name': stock.company_name,
            'currentPrice': float(stock.current_price) if stock.current_price else None,
            'volume': stock.volume,
            'avgVolume': stock.avg_volume_50d,
            'ema22': float(stock.ema_22) if stock.ema_22 else None,
            'ema53': float(stock.ema_53) if stock.ema_53 else None,
            'ema208': float(stock.ema_208) if stock.ema_208 else None,
            'hasEarnings': stock.has_earnings,
            'daysToEarnings': stock.days_to_earnings,
            'earningsDate': stock.earnings_date.isoformat() if stock.earnings_date else None,
            'totalScore': stock.total_score,
            'lastUpdated': stock.last_updated.isoformat() if stock.last_updated else None
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error fetching stock data for {symbol}: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to fetch stock data'
        )