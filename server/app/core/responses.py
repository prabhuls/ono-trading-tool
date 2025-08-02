from typing import TypeVar, Generic, Optional, Any, Dict, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .logging import get_logger, request_id_var


logger = get_logger(__name__)

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """Base response model for all API responses"""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable message about the response")
    data: Optional[T] = Field(None, description="Response data payload")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if request failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    )


class SuccessResponse(BaseResponse[T]):
    """Success response (2xx status codes)"""
    success: bool = True
    error: None = None


class ErrorResponse(BaseResponse[None]):
    """Error response (4xx, 5xx status codes)"""
    success: bool = False
    data: None = None
    error_code: str = Field(..., description="Machine-readable error code")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    
    def build_error(self) -> Dict[str, Any]:
        """Build error object"""
        error_obj = {
            "code": self.error_code,
            "message": self.message,
        }
        if self.error_details:
            error_obj["details"] = self.error_details
        return error_obj


class PaginatedResponse(SuccessResponse[List[T]]):
    """Paginated response for list endpoints"""
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
        message: str = "Success"
    ) -> "PaginatedResponse[T]":
        """Create a paginated response"""
        total_pages = (total + page_size - 1) // page_size
        
        return cls(
            data=items,
            message=message,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            request_id=request_id_var.get()
        )


# Response factory functions
def create_success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    metadata: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Create standardized success response
    
    Args:
        data: Response data payload
        message: Success message
        status_code: HTTP status code (default: 200)
        metadata: Additional metadata
        headers: Additional response headers
        
    Returns:
        JSONResponse with standardized format
    """
    response = SuccessResponse(
        data=data,
        message=message,
        metadata=metadata,
        request_id=request_id_var.get()
    )
    
    logger.debug(f"Success response: {message}", status_code=status_code)
    
    # Build response content for success response
    content = {
        "success": response.success,
        "message": response.message,
        "data": response.data,
        "metadata": response.metadata,
        "request_id": response.request_id,
        "timestamp": response.timestamp.isoformat() if response.timestamp else None.isoformat() if response.timestamp else None
    }
    
    # Remove None values
    content = {k: v for k, v in content.items() if v is not None}
    
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers
    )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_details: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code (default: 400)
        error_details: Additional error context
        headers: Additional response headers
        
    Returns:
        JSONResponse with standardized error format
    """
    response = ErrorResponse(
        error_code=error_code,
        message=message,
        error_details=error_details,
        request_id=request_id_var.get()
    )
    
    logger.warning(
        f"Error response: {message}",
        error_code=error_code,
        status_code=status_code,
        error_details=error_details
    )
    
    # Build response content manually to avoid serialization issues
    content = {
        "success": response.success,
        "message": response.message,
        "error": response.build_error(),  # Call the method to build error object
        "request_id": response.request_id,
        "timestamp": response.timestamp.isoformat() if response.timestamp else None
    }
    
    # Remove None values
    content = {k: v for k, v in content.items() if v is not None}
    
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers
    )


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
    metadata: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create standardized paginated response
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        message: Success message
        metadata: Additional metadata
        
    Returns:
        JSONResponse with pagination metadata
    """
    response = PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        message=message
    )
    
    if metadata:
        response.metadata = metadata
        
    logger.debug(
        f"Paginated response: {message}",
        total=total,
        page=page,
        page_size=page_size
    )
    
    # Build response content for paginated response
    content = {
        "success": response.success,
        "message": response.message,
        "data": response.data,
        "pagination": response.pagination,
        "metadata": response.metadata,
        "request_id": response.request_id,
        "timestamp": response.timestamp.isoformat() if response.timestamp else None
    }
    
    # Remove None values
    content = {k: v for k, v in content.items() if v is not None}
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=content
    )


# Common error responses
class ErrorCode:
    """Common error codes"""
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_REQUEST = "INVALID_REQUEST"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # Business logic errors
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_OPERATION = "INVALID_OPERATION"
    EXPIRED_RESOURCE = "EXPIRED_RESOURCE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


# Predefined error responses
def validation_error(
    message: str = "Validation failed",
    errors: Optional[List[Dict[str, Any]]] = None
) -> JSONResponse:
    """Create validation error response"""
    return create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_details={"validation_errors": errors} if errors else None
    )


def not_found_error(
    resource: str,
    identifier: Optional[Union[str, int]] = None
) -> JSONResponse:
    """Create not found error response"""
    message = f"{resource} not found"
    if identifier:
        message = f"{resource} with id '{identifier}' not found"
        
    return create_error_response(
        error_code=ErrorCode.NOT_FOUND,
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
        error_details={"resource": resource, "identifier": identifier} if identifier else None
    )


def authentication_error(
    message: str = "Authentication required"
) -> JSONResponse:
    """Create authentication error response"""
    return create_error_response(
        error_code=ErrorCode.AUTHENTICATION_REQUIRED,
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"}
    )


def permission_error(
    message: str = "Permission denied"
) -> JSONResponse:
    """Create permission denied error response"""
    return create_error_response(
        error_code=ErrorCode.PERMISSION_DENIED,
        message=message,
        status_code=status.HTTP_403_FORBIDDEN
    )


def rate_limit_error(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None
) -> JSONResponse:
    """Create rate limit error response"""
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)
        
    return create_error_response(
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=message,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        error_details={"retry_after": retry_after} if retry_after else None,
        headers=headers
    )


def internal_error(
    message: str = "An internal error occurred",
    error: Optional[Exception] = None
) -> JSONResponse:
    """Create internal server error response"""
    error_details = None
    if error and logger.logger.isEnabledFor(logger.logger.level):
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
    return create_error_response(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_details=error_details
    )


def external_api_error(
    service: str,
    message: Optional[str] = None
) -> JSONResponse:
    """Create external API error response"""
    default_message = f"External service '{service}' is unavailable"
    
    return create_error_response(
        error_code=ErrorCode.EXTERNAL_API_ERROR,
        message=message or default_message,
        status_code=status.HTTP_502_BAD_GATEWAY,
        error_details={"service": service}
    )