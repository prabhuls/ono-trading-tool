"""Claims API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.claims import Claims
from app.models.stocks import MainList
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/active-claims")
async def get_active_claims(
    db: AsyncSession = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol")
):
    """Get all active claims (not closed)."""
    try:
        query = select(Claims).where(Claims.status != "closed")
        
        if ticker:
            query = query.where(Claims.ticker == ticker.upper())
        
        query = query.order_by(desc(Claims.entry_date))
        
        result = await db.execute(query)
        claims = result.scalars().all()
        
        # Convert to dict format
        claims_data = []
        for claim in claims:
            claim_dict = {
                "id": claim.id,
                "ticker": claim.ticker,
                "entry_date": claim.entry_date.isoformat() if claim.entry_date else None,
                "expiry_date": claim.expiry_date.isoformat() if claim.expiry_date else None,
                "strike_price": float(claim.strike_price) if claim.strike_price else None,
                "entry_price": float(claim.entry_price) if claim.entry_price else None,
                "exit_price": float(claim.exit_price) if claim.exit_price else None,
                "status": claim.status,
                "profit_loss": float(claim.profit_loss) if claim.profit_loss else None,
                "strategy": claim.strategy,
                "notes": claim.notes
            }
            claims_data.append(claim_dict)
        
        return {"claims": claims_data}
        
    except Exception as e:
        logger.error(f"Error fetching active claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/closed-claims")
async def get_closed_claims(
    db: AsyncSession = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    days: int = Query(30, description="Number of days to look back")
):
    """Get closed claims from the last N days."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(Claims).where(
            and_(
                Claims.status == "closed",
                Claims.exit_date >= cutoff_date
            )
        )
        
        if ticker:
            query = query.where(Claims.ticker == ticker.upper())
        
        query = query.order_by(desc(Claims.exit_date))
        
        result = await db.execute(query)
        claims = result.scalars().all()
        
        # Convert to dict format
        claims_data = []
        total_profit_loss = 0
        
        for claim in claims:
            profit_loss = float(claim.profit_loss) if claim.profit_loss else 0
            total_profit_loss += profit_loss
            
            claim_dict = {
                "id": claim.id,
                "ticker": claim.ticker,
                "entry_date": claim.entry_date.isoformat() if claim.entry_date else None,
                "exit_date": claim.exit_date.isoformat() if claim.exit_date else None,
                "expiry_date": claim.expiry_date.isoformat() if claim.expiry_date else None,
                "strike_price": float(claim.strike_price) if claim.strike_price else None,
                "entry_price": float(claim.entry_price) if claim.entry_price else None,
                "exit_price": float(claim.exit_price) if claim.exit_price else None,
                "status": claim.status,
                "profit_loss": profit_loss,
                "strategy": claim.strategy,
                "notes": claim.notes
            }
            claims_data.append(claim_dict)
        
        return {
            "claims": claims_data,
            "total_profit_loss": total_profit_loss,
            "count": len(claims_data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching closed claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_claims_summary(
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics for all claims."""
    try:
        # Get all claims
        result = await db.execute(select(Claims))
        all_claims = result.scalars().all()
        
        # Calculate statistics
        total_claims = len(all_claims)
        active_claims = sum(1 for c in all_claims if c.status != "closed")
        closed_claims = sum(1 for c in all_claims if c.status == "closed")
        
        total_profit = sum(
            float(c.profit_loss) for c in all_claims 
            if c.profit_loss and c.status == "closed" and float(c.profit_loss) > 0
        )
        total_loss = sum(
            float(c.profit_loss) for c in all_claims 
            if c.profit_loss and c.status == "closed" and float(c.profit_loss) < 0
        )
        
        winning_trades = sum(
            1 for c in all_claims 
            if c.profit_loss and c.status == "closed" and float(c.profit_loss) > 0
        )
        losing_trades = sum(
            1 for c in all_claims 
            if c.profit_loss and c.status == "closed" and float(c.profit_loss) < 0
        )
        
        win_rate = (winning_trades / closed_claims * 100) if closed_claims > 0 else 0
        
        return {
            "total_claims": total_claims,
            "active_claims": active_claims,
            "closed_claims": closed_claims,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit_loss": total_profit + total_loss,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2)
        }
        
    except Exception as e:
        logger.error(f"Error fetching claims summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_claim(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new claim entry."""
    try:
        claim = Claims(
            ticker=data.get("ticker"),
            entry_date=datetime.fromisoformat(data.get("entry_date")) if data.get("entry_date") else datetime.utcnow(),
            expiry_date=datetime.fromisoformat(data.get("expiry_date")) if data.get("expiry_date") else None,
            strike_price=data.get("strike_price"),
            entry_price=data.get("entry_price"),
            status=data.get("status", "active"),
            strategy=data.get("strategy", "credit_spread"),
            notes=data.get("notes")
        )
        
        db.add(claim)
        await db.commit()
        await db.refresh(claim)
        
        return {
            "success": True,
            "claim_id": claim.id,
            "message": f"Claim created for {claim.ticker}"
        }
        
    except Exception as e:
        logger.error(f"Error creating claim: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{claim_id}/close")
async def close_claim(
    claim_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Close an existing claim with exit details."""
    try:
        result = await db.execute(
            select(Claims).where(Claims.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        claim.exit_price = data.get("exit_price")
        claim.exit_date = datetime.fromisoformat(data.get("exit_date")) if data.get("exit_date") else datetime.utcnow()
        claim.status = "closed"
        
        # Calculate profit/loss
        if claim.entry_price and claim.exit_price:
            claim.profit_loss = float(claim.exit_price) - float(claim.entry_price)
        
        if data.get("notes"):
            claim.notes = (claim.notes or "") + f"\nExit: {data.get('notes')}"
        
        await db.commit()
        await db.refresh(claim)
        
        return {
            "success": True,
            "claim_id": claim.id,
            "profit_loss": float(claim.profit_loss) if claim.profit_loss else 0,
            "message": f"Claim closed for {claim.ticker}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing claim: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))