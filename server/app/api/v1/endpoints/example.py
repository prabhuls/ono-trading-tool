from fastapi import APIRouter, Query, Path, Body, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.responses import (
    create_success_response,
    create_error_response,
    create_paginated_response,
    not_found_error,
    ErrorCode
)
from app.core.cache import cache
from app.core.logging import get_logger
from app.core.monitoring import monitor_performance, capture_errors


logger = get_logger(__name__)
router = APIRouter()


# Example request/response models
class ExampleRequest(BaseModel):
    """Example request model"""
    name: str = Field(..., min_length=1, max_length=100, description="Name field")
    value: int = Field(..., ge=0, le=1000, description="Value between 0 and 1000")
    tags: Optional[List[str]] = Field(None, description="Optional tags")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Example Item",
                "value": 42,
                "tags": ["tag1", "tag2"]
            }
        }


class ExampleResponse(BaseModel):
    """Example response model"""
    id: str
    name: str
    value: int
    tags: List[str]
    created_at: str


# Example endpoints demonstrating various patterns
@router.get("/items", response_model=List[ExampleResponse])
@cache(ttl=300, namespace="example")
async def list_items(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query")
) -> JSONResponse:
    """
    List items with pagination
    
    This endpoint demonstrates:
    - Pagination
    - Query parameters
    - Caching
    - Standardized responses
    """
    logger.info("Listing items", page=page, page_size=page_size, search=search)
    
    # Simulate fetching data
    total_items = 100
    items = []
    
    start = (page - 1) * page_size
    end = start + page_size
    
    for i in range(start, min(end, total_items)):
        items.append({
            "id": f"item-{i+1}",
            "name": f"Item {i+1}",
            "value": (i + 1) * 10,
            "tags": ["example", "demo"],
            "created_at": "2024-01-01T00:00:00Z"
        })
        
    return create_paginated_response(
        items=items,
        total=total_items,
        page=page,
        page_size=page_size,
        message="Items retrieved successfully"
    )


@router.get("/items/{item_id}", response_model=ExampleResponse)
@monitor_performance("api.get_item")
async def get_item(
    item_id: str = Path(..., description="Item ID")
) -> JSONResponse:
    """
    Get a single item by ID
    
    This endpoint demonstrates:
    - Path parameters
    - Performance monitoring
    - Error handling
    """
    logger.info("Getting item", item_id=item_id)
    
    # Simulate item lookup
    if not item_id.startswith("item-"):
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
    item_data = {
        "id": item_id,
        "name": f"Item {item_id.split('-')[1]}",
        "value": 100,
        "tags": ["example", "demo"],
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    return create_success_response(
        data=item_data,
        message=f"Item {item_id} retrieved successfully",
        metadata={"source": "database"}
    )


@router.post("/items", response_model=ExampleResponse, status_code=201)
@capture_errors(level="warning")
async def create_item(
    item: ExampleRequest = Body(..., description="Item to create")
) -> JSONResponse:
    """
    Create a new item
    
    This endpoint demonstrates:
    - POST requests with body
    - Request validation
    - Error capture decorator
    - 201 status code
    """
    logger.info("Creating item", name=item.name, value=item.value)
    
    # Simulate item creation
    new_item = {
        "id": f"item-{item.value}",
        "name": item.name,
        "value": item.value,
        "tags": item.tags or [],
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    # Log business event
    logger.log_business_event(
        event_type="item_created",
        data={"item_id": new_item["id"], "name": item.name}
    )
    
    return create_success_response(
        data=new_item,
        message="Item created successfully",
        status_code=201
    )


@router.put("/items/{item_id}", response_model=ExampleResponse)
async def update_item(
    item_id: str = Path(..., description="Item ID"),
    item: ExampleRequest = Body(..., description="Updated item data")
) -> JSONResponse:
    """
    Update an existing item
    
    This endpoint demonstrates:
    - PUT requests
    - Path and body parameters
    - Update operations
    """
    logger.info("Updating item", item_id=item_id)
    
    # Check if item exists
    if not item_id.startswith("item-"):
        return not_found_error("Item", item_id)
        
    # Simulate update
    updated_item = {
        "id": item_id,
        "name": item.name,
        "value": item.value,
        "tags": item.tags or [],
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    return create_success_response(
        data=updated_item,
        message=f"Item {item_id} updated successfully"
    )


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str = Path(..., description="Item ID")
) -> JSONResponse:
    """
    Delete an item
    
    This endpoint demonstrates:
    - DELETE requests
    - No response body pattern
    - Success with 204 alternative
    """
    logger.info("Deleting item", item_id=item_id)
    
    # Check if item exists
    if not item_id.startswith("item-"):
        return not_found_error("Item", item_id)
        
    # Simulate deletion
    logger.log_business_event(
        event_type="item_deleted",
        data={"item_id": item_id}
    )
    
    return create_success_response(
        message=f"Item {item_id} deleted successfully"
    )


@router.post("/items/batch")
async def process_batch(
    items: List[ExampleRequest] = Body(..., description="Items to process")
) -> JSONResponse:
    """
    Process multiple items in batch
    
    This endpoint demonstrates:
    - Batch operations
    - List input validation
    - Partial success handling
    """
    logger.info("Processing batch", count=len(items))
    
    results = []
    errors = []
    
    for i, item in enumerate(items):
        try:
            # Simulate processing
            if item.value > 500:
                errors.append({
                    "index": i,
                    "error": "Value too high",
                    "item": item.dict()
                })
            else:
                results.append({
                    "id": f"item-{item.value}",
                    "name": item.name,
                    "value": item.value,
                    "tags": item.tags or [],
                    "created_at": "2024-01-01T00:00:00Z"
                })
        except Exception as e:
            errors.append({
                "index": i,
                "error": str(e),
                "item": item.dict()
            })
            
    # Return appropriate response based on results
    if errors and not results:
        return create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="All items failed processing",
            error_details={"errors": errors}
        )
    elif errors:
        return create_success_response(
            data={
                "processed": results,
                "failed": errors
            },
            message=f"Processed {len(results)} items with {len(errors)} errors",
            metadata={"partial_success": True}
        )
    else:
        return create_success_response(
            data={"processed": results},
            message=f"Successfully processed {len(results)} items"
        )


@router.get("/external-data")
@cache(ttl=600, namespace="external_api")
async def get_external_data() -> JSONResponse:
    """
    Example endpoint that calls external API
    
    This endpoint demonstrates:
    - External API integration
    - Caching external responses
    - Error handling for external services
    """
    try:
        # This would call your external service
        # from app.services.external.polygon_service import polygon_service
        # data = await polygon_service.get_market_status()
        
        # Simulated external data
        data = {
            "market": "open",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        return create_success_response(
            data=data,
            message="External data retrieved successfully",
            metadata={"source": "external_api", "cached": False}
        )
        
    except Exception as e:
        logger.error("Failed to fetch external data", error=e)
        return create_error_response(
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            message="Failed to fetch external data",
            status_code=502
        )