import time
import uuid
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, set_request_id, set_user_id, clear_context
from app.core.responses import rate_limit_error
from app.core.monitoring import ErrorMonitoring
from app.core.config import settings


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        set_request_id(request_id)
        
        # Extract user ID from auth header or token (implement based on your auth)
        user_id = self._extract_user_id(request)
        if user_id:
            set_user_id(user_id)
            
        # Get client info
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent", "")
        
        # Log request
        logger.log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            client_ip=client_ip,
            user_agent=user_agent,
            query_params=dict(request.query_params),
            request_id=request_id
        )
        
        # Add breadcrumb for Sentry
        ErrorMonitoring.add_breadcrumb(
            message=f"{request.method} {request.url.path}",
            category="request",
            level="info",
            data={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params)
            }
        )
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.log_api_response(
                status_code=response.status_code,
                response_time=process_time,
                endpoint=str(request.url.path),
                request_id=request_id
            )
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request processing error",
                error=e,
                endpoint=str(request.url.path),
                method=request.method,
                process_time=process_time
            )
            
            # Re-raise to be handled by exception handlers
            raise
            
        finally:
            # Clear context
            clear_context()
            
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request (implement based on your auth system)
        """
        # Example: Extract from JWT token in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Decode JWT and extract user_id
            # This is just a placeholder - implement actual JWT decoding
            return None
            
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Store request counts by IP
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # Cleanup old entries every minute
        self.last_cleanup = datetime.now()
        
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", f"{settings.api.prefix}/health"]:
            return await call_next(request)
            
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Cleanup old entries periodically
        now = datetime.now()
        if (now - self.last_cleanup).seconds > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
            
        # Check rate limit
        if not self._check_rate_limit(client_ip):
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path
            )
            
            # Calculate retry after
            retry_after = self._get_retry_after(client_ip)
            
            return rate_limit_error(
                message=f"Rate limit exceeded. Please retry after {retry_after} seconds",
                retry_after=retry_after
            )
            
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(settings.api.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(self._get_reset_time(client_ip).timestamp()))
        
        return response
        
    def _check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if request is within rate limit
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=settings.api.rate_limit_period)
        
        # Get requests in current window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[client_ip]) >= settings.api.rate_limit_requests:
            return False
            
        # Add current request
        self.requests[client_ip].append(now)
        return True
        
    def _get_remaining_requests(self, client_ip: str) -> int:
        """
        Get remaining requests in current window
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=settings.api.rate_limit_period)
        
        current_requests = len([
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ])
        
        return max(0, settings.api.rate_limit_requests - current_requests)
        
    def _get_reset_time(self, client_ip: str) -> datetime:
        """
        Get time when rate limit resets
        """
        if not self.requests[client_ip]:
            return datetime.now()
            
        # Find oldest request in current window
        oldest_request = min(self.requests[client_ip])
        return oldest_request + timedelta(seconds=settings.api.rate_limit_period)
        
    def _get_retry_after(self, client_ip: str) -> int:
        """
        Get seconds until rate limit resets
        """
        reset_time = self._get_reset_time(client_ip)
        retry_after = (reset_time - datetime.now()).total_seconds()
        return max(1, int(retry_after))
        
    def _cleanup_old_entries(self):
        """
        Remove old entries to prevent memory growth
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=settings.api.rate_limit_period)
        
        # Clean up IPs with no recent requests
        empty_ips = []
        for ip, requests in self.requests.items():
            self.requests[ip] = [
                req_time for req_time in requests
                if req_time > window_start
            ]
            if not self.requests[ip]:
                empty_ips.append(ip)
                
        # Remove empty entries
        for ip in empty_ips:
            del self.requests[ip]