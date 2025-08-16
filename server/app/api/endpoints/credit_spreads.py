"""
Credit Spread Trade Management API Endpoints
Handles claiming, retrieving, and managing user's credit spread trades
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_async_session
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.trades import CreditSpread

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ClaimCreditSpreadRequest(BaseModel):
    """Request model for claiming a credit spread trade"""
    ticker: str
    current_price: float
    short_strike: float
    long_strike: float
    net_credit: float
    max_risk: float
    roi: float
    expiration: str  # ISO format date string
    contract_type: str  # "call" or "put"
    days_to_expiration: int
    breakeven: float
    buffer_room: float
    scenarios: Optional[List[Dict[str, Any]]] = None
    spread_type: Optional[str] = None
    sell_contract: Optional[str] = None
    buy_contract: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "TSLA",
                "current_price": 331.21,
                "short_strike": 320.0,
                "long_strike": 315.0,
                "net_credit": 1.25,
                "max_risk": 3.75,
                "roi": 33.33,
                "expiration": "2025-01-17",
                "contract_type": "put",
                "days_to_expiration": 7,
                "breakeven": 318.75,
                "buffer_room": 3.89,
                "scenarios": []
            }
        }
    }


class UpdateTradeStatusRequest(BaseModel):
    """Request model for updating trade status"""
    trade_status: str = Field(..., pattern="^(saved|claimed|closed)$")
    closed_price: Optional[float] = None
    profit_loss: Optional[float] = None


@router.post("/claim", response_model=Dict[str, Any])
async def claim_credit_spread(
    request: ClaimCreditSpreadRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Claim a credit spread trade for the authenticated user
    
    This endpoint saves a credit spread analysis to the user's portfolio
    for tracking and management.
    """
    try:
        logger.info(f"User {current_user.id} claiming credit spread for {request.ticker}")
        
        # Parse expiration date
        try:
            expiration_date = datetime.strptime(request.expiration, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid expiration date format. Use YYYY-MM-DD"
            )
        
        # Create new credit spread trade
        new_spread = CreditSpread(
            id=str(uuid4()),
            user_id=current_user.id,
            ticker=request.ticker.upper(),
            current_price=Decimal(str(request.current_price)),
            short_strike=Decimal(str(request.short_strike)),
            long_strike=Decimal(str(request.long_strike)),
            net_credit=Decimal(str(request.net_credit)),
            max_risk=Decimal(str(request.max_risk)),
            roi=Decimal(str(request.roi)),
            expiration=expiration_date,
            contract_type=request.contract_type.lower(),
            days_to_expiration=request.days_to_expiration,
            breakeven=Decimal(str(request.breakeven)),
            buffer_room=Decimal(str(request.buffer_room)),
            scenarios=request.scenarios,
            trade_status="claimed",
            claimed_at=datetime.utcnow()
        )
        
        # Add to session and commit
        session.add(new_spread)
        await session.commit()
        await session.refresh(new_spread)
        
        logger.info(f"Successfully claimed credit spread {new_spread.id} for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Credit spread claimed successfully",
            "trade": new_spread.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming credit spread: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to claim credit spread: {str(e)}"
        )


@router.get("/user-trades", response_model=Dict[str, Any])
async def get_user_trades(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all credit spread trades for the authenticated user
    
    Query parameters:
    - status: Filter by trade status (saved, claimed, closed)
    - limit: Maximum number of trades to return
    - offset: Number of trades to skip (for pagination)
    """
    try:
        logger.info(f"Fetching trades for user {current_user.id}, status={status}")
        
        # Build query
        query = select(CreditSpread).where(CreditSpread.user_id == current_user.id)
        
        # Apply status filter if provided
        if status:
            if status not in ["saved", "claimed", "closed"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid status. Must be 'saved', 'claimed', or 'closed'"
                )
            query = query.where(CreditSpread.trade_status == status)
        
        # Order by creation date (newest first) and apply pagination
        query = query.order_by(desc(CreditSpread.created_at)).limit(limit).offset(offset)
        
        # Execute query
        result = await session.execute(query)
        trades = result.scalars().all()
        
        # Get total count for pagination
        count_query = select(CreditSpread).where(CreditSpread.user_id == current_user.id)
        if status:
            count_query = count_query.where(CreditSpread.trade_status == status)
        count_result = await session.execute(count_query)
        total_count = len(count_result.scalars().all())
        
        # Convert to dict format
        trades_data = [trade.to_dict() for trade in trades]
        
        # Separate by status for frontend
        active_trades = [t for t in trades_data if t["tradeStatus"] in ["saved", "claimed"]]
        closed_trades = [t for t in trades_data if t["tradeStatus"] == "closed"]
        
        logger.info(f"Found {len(trades)} trades for user {current_user.id}")
        
        return {
            "success": True,
            "trades": trades_data,
            "activeTrades": active_trades,
            "closedTrades": closed_trades,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user trades: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trades: {str(e)}"
        )


@router.put("/{trade_id}/status", response_model=Dict[str, Any])
async def update_trade_status(
    trade_id: str,
    request: UpdateTradeStatusRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update the status of a credit spread trade
    
    Allows closing a trade with P&L tracking
    """
    try:
        # Fetch the trade
        result = await session.execute(
            select(CreditSpread).where(
                and_(
                    CreditSpread.id == trade_id,
                    CreditSpread.user_id == current_user.id
                )
            )
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(
                status_code=404,
                detail="Trade not found or you don't have permission to modify it"
            )
        
        # Update trade status
        trade.trade_status = request.trade_status
        
        # If closing the trade, update closing details
        if request.trade_status == "closed":
            trade.closed_at = datetime.utcnow()
            if request.closed_price is not None:
                trade.closed_price = Decimal(str(request.closed_price))
            if request.profit_loss is not None:
                trade.profit_loss = Decimal(str(request.profit_loss))
        elif request.trade_status == "claimed" and not trade.claimed_at:
            trade.claimed_at = datetime.utcnow()
        
        trade.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(trade)
        
        logger.info(f"Updated trade {trade_id} status to {request.trade_status}")
        
        return {
            "success": True,
            "message": f"Trade status updated to {request.trade_status}",
            "trade": trade.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trade status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update trade status: {str(e)}"
        )


@router.delete("/{trade_id}", response_model=Dict[str, Any])
async def delete_trade(
    trade_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a credit spread trade
    
    Only the owner of the trade can delete it
    """
    try:
        # Fetch the trade
        result = await session.execute(
            select(CreditSpread).where(
                and_(
                    CreditSpread.id == trade_id,
                    CreditSpread.user_id == current_user.id
                )
            )
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(
                status_code=404,
                detail="Trade not found or you don't have permission to delete it"
            )
        
        # Delete the trade
        await session.delete(trade)
        await session.commit()
        
        logger.info(f"Deleted trade {trade_id} for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Trade deleted successfully",
            "deletedTradeId": trade_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trade: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete trade: {str(e)}"
        )


@router.get("/{trade_id}", response_model=Dict[str, Any])
async def get_trade_by_id(
    trade_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific credit spread trade by ID
    
    Only the owner of the trade can view it
    """
    try:
        # Fetch the trade
        result = await session.execute(
            select(CreditSpread).where(
                and_(
                    CreditSpread.id == trade_id,
                    CreditSpread.user_id == current_user.id
                )
            )
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(
                status_code=404,
                detail="Trade not found or you don't have permission to view it"
            )
        
        return {
            "success": True,
            "trade": trade.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trade: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trade: {str(e)}"
        )