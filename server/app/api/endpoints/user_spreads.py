"""
User Claimed Spreads API Endpoints
Simple implementation matching CashFlowAgent VIP reference
Stores trades directly with JWT user ID, no complex user management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header, Cookie
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.oct_auth import verify_oct_token, OCTTokenPayload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/claim")
async def claim_spread(
    spread_data: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    jwt_payload: Optional[OCTTokenPayload] = Depends(verify_oct_token)
):
    """
    Claim a credit spread - stores directly with JWT user ID
    Matches the reference implementation exactly
    """
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Extract user ID directly from JWT (like reference)
        user_id = jwt_payload.sub  # This is the JWT sub field
        symbol = spread_data.get("ticker", "UNKNOWN").upper()
        
        logger.info(f"Claiming spread for user {user_id}, symbol {symbol}")
        
        # Store in user_claimed_spreads table (exactly like reference)
        query = text("""
            INSERT INTO user_claimed_spreads 
            (user_id, symbol, spread_data, claimed_at, status)
            VALUES (:user_id, :symbol, :spread_data, :claimed_at, :status)
            RETURNING id
        """)
        
        result = await session.execute(
            query,
            {
                "user_id": user_id,  # JWT sub directly
                "symbol": symbol,
                "spread_data": json.dumps(spread_data),  # Store as JSON string
                "claimed_at": datetime.utcnow(),
                "status": "active"
            }
        )
        
        spread_id = result.scalar()
        await session.commit()
        
        logger.info(f"Successfully claimed spread {spread_id} for user {user_id}")
        
        return {
            "success": True,
            "id": spread_id,
            "message": "Credit spread claimed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error claiming spread: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to claim spread: {str(e)}"
        )


@router.get("/user-claims")
async def get_user_claims(
    session: AsyncSession = Depends(get_async_session),
    jwt_payload: Optional[OCTTokenPayload] = Depends(verify_oct_token)
):
    """
    Get all claimed spreads for the authenticated user
    Returns data exactly like the reference implementation
    """
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_id = jwt_payload.sub
        
        logger.info(f"Fetching claims for user {user_id}")
        
        # Query user's claimed spreads
        query = text("""
            SELECT id, user_id, symbol, spread_data, claimed_at, status, expiration_date, notes
            FROM user_claimed_spreads
            WHERE user_id = :user_id
            ORDER BY claimed_at DESC
        """)
        
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        # Format response like reference
        claims = []
        for row in rows:
            claims.append({
                "id": row.id,
                "userId": row.user_id,
                "symbol": row.symbol,
                "spreadData": json.loads(row.spread_data) if row.spread_data else {},
                "claimedAt": row.claimed_at.isoformat() if row.claimed_at else None,
                "status": row.status,
                "expirationDate": row.expiration_date.isoformat() if row.expiration_date else None,
                "notes": row.notes
            })
        
        logger.info(f"Found {len(claims)} claims for user {user_id}")
        
        # Separate active and closed for frontend
        active_claims = [c for c in claims if c["status"] in ["active", "pending"]]
        closed_claims = [c for c in claims if c["status"] == "closed"]
        
        return {
            "claims": claims,
            "activeTrades": active_claims,
            "closedTrades": closed_claims,
            "total": len(claims)
        }
        
    except Exception as e:
        logger.error(f"Error fetching user claims: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch claims: {str(e)}"
        )


@router.delete("/{spread_id}")
async def delete_spread(
    spread_id: int,
    session: AsyncSession = Depends(get_async_session),
    jwt_payload: Optional[OCTTokenPayload] = Depends(verify_oct_token)
):
    """
    Delete a claimed spread (only if owned by user)
    """
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_id = jwt_payload.sub
        
        logger.info(f"Deleting spread {spread_id} for user {user_id}")
        
        # Delete only if owned by user
        query = text("""
            DELETE FROM user_claimed_spreads
            WHERE id = :spread_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = await session.execute(
            query,
            {"spread_id": spread_id, "user_id": user_id}
        )
        
        deleted_id = result.scalar()
        await session.commit()
        
        if not deleted_id:
            raise HTTPException(
                status_code=404,
                detail="Spread not found or unauthorized"
            )
        
        logger.info(f"Deleted spread {spread_id}")
        
        return {
            "success": True,
            "message": "Spread deleted successfully",
            "deletedId": spread_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting spread: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete spread: {str(e)}"
        )


@router.put("/{spread_id}/status")
async def update_spread_status(
    spread_id: int,
    status_update: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    jwt_payload: Optional[OCTTokenPayload] = Depends(verify_oct_token)
):
    """
    Update spread status (active, closed, expired)
    """
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_id = jwt_payload.sub
        new_status = status_update.get("status", "active")
        notes = status_update.get("notes")
        
        logger.info(f"Updating spread {spread_id} status to {new_status}")
        
        # Update only if owned by user
        query = text("""
            UPDATE user_claimed_spreads
            SET status = :status, notes = :notes
            WHERE id = :spread_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = await session.execute(
            query,
            {
                "status": new_status,
                "notes": notes,
                "spread_id": spread_id,
                "user_id": user_id
            }
        )
        
        updated_id = result.scalar()
        await session.commit()
        
        if not updated_id:
            raise HTTPException(
                status_code=404,
                detail="Spread not found or unauthorized"
            )
        
        logger.info(f"Updated spread {spread_id} status to {new_status}")
        
        return {
            "success": True,
            "message": f"Status updated to {new_status}",
            "spreadId": spread_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating spread status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update status: {str(e)}"
        )