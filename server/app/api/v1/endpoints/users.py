"""
User management endpoints demonstrating SQLAlchemy usage
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext  # type: ignore[import-untyped]

from app.core.dependencies import get_db, require_database
from app.core.responses import create_success_response, create_error_response
from app.core.cache import cache, cache_manager
from app.models.user import User
from app.utils.database import DatabaseCRUD, PaginationParams
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create CRUD instance for User model
user_crud = DatabaseCRUD[User](User)


@router.post("/", response_model=UserResponse)
@require_database
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user"""
    # Check if user already exists
    if await user_crud.exists(db, email=user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_in.username and await user_crud.exists(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Hash password
    hashed_password = pwd_context.hash(user_in.password)
    
    # Create user
    user_data = user_in.dict(exclude={"password"})
    user_data["hashed_password"] = hashed_password
    
    user = await user_crud.create(db, obj_in=user_data)
    
    return create_success_response(
        data=UserResponse.from_orm(user),
        message="User created successfully"
    )


@router.get("/", response_model=UserListResponse)
@require_database
@cache(ttl=60, namespace="users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List users with pagination"""
    pagination = PaginationParams(page=page, per_page=per_page)
    
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    
    result = await user_crud.get_paginated(
        db,
        pagination=pagination,
        filters=filters,
        order_by="-created_at"
    )
    
    return create_success_response(
        data={
            "items": [UserResponse.from_orm(user) for user in result.items],
            "pagination": {
                "total": result.total,
                "page": result.page,
                "per_page": result.per_page,
                "pages": result.pages,
                "has_prev": result.has_prev,
                "has_next": result.has_next
            }
        },
        message="Users retrieved successfully"
    )


@router.get("/{user_id}", response_model=UserResponse)
@require_database
@cache(ttl=300, namespace="users")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user by ID"""
    user = await user_crud.get(
        db,
        id=user_id,
        load_relationships=["api_keys", "watchlists"]
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return create_success_response(
        data=UserResponse.from_orm(user),
        message="User retrieved successfully"
    )


@router.patch("/{user_id}", response_model=UserResponse)
@require_database
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user information"""
    user = await user_crud.get(db, id=user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
    
    # Update timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    user = await user_crud.update(db, db_obj=user, obj_in=update_data)
    
    # Invalidate cache
    await cache_manager.delete(f"user:{user_id}", namespace="users")
    
    return create_success_response(
        data=UserResponse.from_orm(user),
        message="User updated successfully"
    )


@router.delete("/{user_id}")
@require_database
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a user"""
    success = await user_crud.delete(db, id=user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Invalidate cache
    await cache_manager.delete(f"user:{user_id}", namespace="users")
    await cache_manager.delete_pattern("*", namespace="users")
    
    return create_success_response(
        message="User deleted successfully"
    )


@router.get("/{user_id}/watchlists")
@require_database
async def get_user_watchlists(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all watchlists for a user"""
    user = await user_crud.get(
        db,
        id=user_id,
        load_relationships=["watchlists"]
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return create_success_response(
        data=[{
            "id": w.id,
            "name": w.name,
            "symbol_count": w.symbol_count,
            "created_at": w.created_at.isoformat()
        } for w in user.watchlists],
        message="Watchlists retrieved successfully"
    )