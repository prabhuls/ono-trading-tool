"""
Database utility functions for common operations
"""
from typing import TypeVar, Type, Generic, List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=Base)
P = TypeVar("P")


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    per_page: int = 50
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseModel, Generic[P]):
    """Paginated response model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    items: List[P]
    total: int
    page: int
    per_page: int
    pages: int
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1
    
    @property
    def has_next(self) -> bool:
        return self.page < self.pages


class DatabaseCRUD(Generic[T]):
    """Generic CRUD operations for database models"""
    
    def __init__(self, model: Type[T]):
        self.model = model
    
    async def get(
        self,
        db: AsyncSession,
        id: Any,
        load_relationships: Optional[List[str]] = None
    ) -> Optional[T]:
        """Get a single record by ID"""
        query = select(self.model).filter(self.model.id == id)  # type: ignore[attr-defined]
        
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[T]:
        """Get multiple records with optional filtering"""
        query = select(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                query = query.order_by(getattr(self.model, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(self.model, order_by))
        
        # Load relationships
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_paginated(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        load_relationships: Optional[List[str]] = None
    ) -> PaginatedResponse[T]:
        """Get paginated records"""
        # Get total count
        count_query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    count_query = count_query.filter(getattr(self.model, key) == value)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get items
        items = await self.get_multi(
            db,
            skip=pagination.offset,
            limit=pagination.per_page,
            filters=filters,
            order_by=order_by,
            load_relationships=load_relationships
        )
        
        # Calculate pages
        pages = (total + pagination.per_page - 1) // pagination.per_page if total else 0
        
        return PaginatedResponse(
            items=items,
            total=total or 0,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=pages
        )
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Dict[str, Any]
    ) -> T:
        """Create a new record"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: T,
        obj_in: Dict[str, Any]
    ) -> T:
        """Update an existing record"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Any
    ) -> bool:
        """Delete a record by ID"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
            return True
        return False
    
    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count records with optional filtering"""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def exists(
        self,
        db: AsyncSession,
        **kwargs
    ) -> bool:
        """Check if a record exists with given criteria"""
        query = select(self.model.id)  # type: ignore[attr-defined]
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        query = query.limit(1)
        result = await db.execute(query)
        return result.scalar() is not None


# Utility functions for common database operations
async def get_or_create(
    db: AsyncSession,
    model: Type[T],
    defaults: Optional[Dict[str, Any]] = None,
    **kwargs
) -> tuple[T, bool]:
    """Get an existing object or create a new one"""
    query = select(model)
    for key, value in kwargs.items():
        query = query.filter(getattr(model, key) == value)
    
    result = await db.execute(query)
    instance = result.scalar_one_or_none()
    
    if instance:
        return instance, False
    
    # Create new instance
    params = {**kwargs}
    if defaults:
        params.update(defaults)
    
    instance = model(**params)
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    
    return instance, True


async def bulk_create(
    db: AsyncSession,
    model: Type[T],
    objects: List[Dict[str, Any]]
) -> List[T]:
    """Bulk create multiple objects"""
    instances = [model(**obj) for obj in objects]
    db.add_all(instances)
    await db.commit()
    
    # Refresh all instances
    for instance in instances:
        await db.refresh(instance)
    
    return instances


async def bulk_update(
    db: AsyncSession,
    model: Type[T],
    updates: List[Dict[str, Any]]
) -> int:
    """
    Bulk update records. Each dict in updates must have 'id' field.
    Returns number of updated records.
    """
    count = 0
    for update in updates:
        if 'id' not in update:
            logger.warning(f"Skipping update without ID: {update}")
            continue
        
        obj_id = update.pop('id')
        query = select(model).filter(model.id == obj_id)  # type: ignore[attr-defined]
        result = await db.execute(query)
        obj = result.scalar_one_or_none()
        
        if obj:
            for field, value in update.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)
            count += 1
    
    await db.commit()
    return count