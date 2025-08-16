import httpx
import asyncio
import time
from typing import Dict, Any, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from app.core.logging import get_logger
from app.core.cache import redis_cache
from app.core.monitoring import monitor_performance, ErrorMonitoring
from app.core.config import settings


logger = get_logger(__name__)

T = TypeVar('T')


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire rate limit slot"""
        async with self._lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                await asyncio.sleep(sleep_time)
                
            self.last_call_time = time.time()


class ExternalAPIError(Exception):
    """Base exception for external API errors"""
    
    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None
    ):
        super().__init__(message)
        self.service = service
        self.status_code = status_code
        self.response_data = response_data


class ExternalAPIService(ABC, Generic[T]):
    """
    Base class for all external API integrations with:
    - Automatic retries with exponential backoff
    - Rate limiting
    - Response caching
    - Error handling
    - Metrics collection
    - Request/response logging
    """
    
    def __init__(
        self,
        service_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit: Optional[float] = None,
        cache_ttl: Optional[int] = 300,
        headers: Optional[Dict[str, str]] = None
    ):
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit else None
        
        # Setup HTTP client
        self.headers = headers or {}
        self._setup_headers()
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers=self.headers,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            follow_redirects=True
        )
        
        # Metrics - using Any to avoid complex type casting
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_response_time": 0.0,
            "errors_by_type": {}
        }
        
        self.logger = get_logger(f"external.{service_name}")
        
    def _setup_headers(self):
        """Setup default headers including authentication"""
        if self.api_key:
            # Common API key header patterns
            if self.service_name.lower() in ["polygon", "alpaca"]:
                self.headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                # Default to X-API-Key
                self.headers["X-API-Key"] = self.api_key
                
        # Add common headers
        self.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"{settings.api.title}/{settings.api.version}"
        })
        
    @abstractmethod
    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for the request - must be implemented by subclass"""
        pass
        
    @abstractmethod
    def _parse_error_response(self, response: httpx.Response) -> str:
        """Parse error message from response - must be implemented by subclass"""
        pass
        
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if request should be retried"""
        if attempt >= self.max_retries:
            return False
            
        # Retry on network errors
        if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
            return True
            
        # Retry on specific HTTP status codes
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code in [429, 500, 502, 503, 504]
            
        return False
        
    def _get_retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        """Calculate retry delay with exponential backoff"""
        # Check for Retry-After header
        if response and "Retry-After" in response.headers:
            try:
                return float(response.headers["Retry-After"])
            except ValueError:
                pass
                
        # Exponential backoff: 1s, 2s, 4s, 8s...
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** attempt), max_delay)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)
        
        return delay + jitter
        
    @monitor_performance("external_api_request")
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with all the bells and whistles
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be joined with base_url)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            use_cache: Whether to use caching for GET requests
            cache_ttl: Override default cache TTL
            
        Returns:
            Parsed JSON response
            
        Raises:
            ExternalAPIError: On API errors
        """
        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()
            
        # Try cache for GET requests
        cache_key = None
        if method == "GET" and use_cache and self.cache_ttl:
            cache_key = self._get_cache_key(endpoint, params)
            cached_response = redis_cache.get(
                cache_key,
                namespace=f"external_api:{self.service_name}"
            )
            if cached_response is not None:
                self.metrics["cache_hits"] += 1
                self.logger.log_cache_hit(cache_key, service=self.service_name)
                return cached_response
                
        # Prepare request
        url = endpoint if endpoint.startswith("http") else urljoin(self.base_url, endpoint)
        request_headers = {**self.headers, **(headers or {})}
        
        # Log request
        self.logger.log_external_api_call(
            service=self.service_name,
            endpoint=endpoint,
            method=method,
            params=params
        )
        
        # Retry loop
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries):
            start_time = time.time()
            
            try:
                # Make request
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers
                )
                
                # Record response time
                response_time = time.time() - start_time
                self.metrics["total_response_time"] += response_time
                
                # Check status
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Log successful response
                self.logger.log_external_api_response(
                    service=self.service_name,
                    status_code=response.status_code,
                    response_time=response_time
                )
                
                # Update metrics
                self.metrics["total_requests"] += 1
                self.metrics["successful_requests"] += 1
                
                # Cache successful GET responses
                if method == "GET" and use_cache and cache_key:
                    ttl = cache_ttl or self.cache_ttl
                    redis_cache.set(
                        cache_key,
                        data,
                        ttl=ttl,
                        namespace=f"external_api:{self.service_name}"
                    )
                    
                # Add breadcrumb for monitoring
                ErrorMonitoring.add_breadcrumb(
                    message=f"External API call to {self.service_name}",
                    category="external_api",
                    level="info",
                    data={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_time_ms": round(response_time * 1000, 2)
                    }
                )
                
                return data
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                error_message = self._parse_error_response(e.response)
                
                self.logger.warning(
                    f"HTTP error from {self.service_name}",
                    status_code=e.response.status_code,
                    error_message=error_message,
                    attempt=attempt + 1
                )
                
                # Update error metrics
                error_type = f"http_{e.response.status_code}"
                self.metrics["errors_by_type"][error_type] = \
                    self.metrics["errors_by_type"].get(error_type, 0) + 1
                    
                # Check if should retry
                if not self._should_retry(e, attempt + 1):
                    break
                    
                # Wait before retry
                retry_delay = self._get_retry_delay(attempt, e.response)
                self.logger.info(
                    f"Retrying request to {self.service_name}",
                    attempt=attempt + 1,
                    retry_delay=retry_delay
                )
                await asyncio.sleep(retry_delay)
                
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                
                self.logger.error(
                    f"Network error calling {self.service_name}",
                    error=e,
                    attempt=attempt + 1
                )
                
                # Update error metrics
                error_type = type(e).__name__
                self.metrics["errors_by_type"][error_type] = \
                    self.metrics["errors_by_type"].get(error_type, 0) + 1
                    
                # Check if should retry
                if not self._should_retry(e, attempt + 1):
                    break
                    
                # Wait before retry
                retry_delay = self._get_retry_delay(attempt)
                await asyncio.sleep(retry_delay)
                
            except Exception as e:
                last_exception = e
                self.logger.error(
                    f"Unexpected error calling {self.service_name}",
                    error=e,
                    error_type=type(e).__name__
                )
                break
                
        # All retries failed
        self.metrics["total_requests"] += 1
        self.metrics["failed_requests"] += 1
        
        # Capture exception to Sentry
        if last_exception:
            ErrorMonitoring.capture_exception(
                last_exception,
                context={
                    "service": self.service_name,
                    "endpoint": endpoint,
                    "method": method,
                    "attempts": self.max_retries
                }
            )
            
        # Raise our custom exception
        if isinstance(last_exception, httpx.HTTPStatusError):
            raise ExternalAPIError(
                message=f"API call to {self.service_name} failed: {self._parse_error_response(last_exception.response)}",
                service=self.service_name,
                status_code=last_exception.response.status_code,
                response_data=last_exception.response.text
            )
        else:
            raise ExternalAPIError(
                message=f"API call to {self.service_name} failed: {str(last_exception)}",
                service=self.service_name
            )
            
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params, **kwargs)
        
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request("POST", endpoint, json_data=json_data, **kwargs)
        
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, json_data=json_data, **kwargs)
        
    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint, **kwargs)
        
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        total_requests = self.metrics["total_requests"]
        if total_requests > 0:
            success_rate = self.metrics["successful_requests"] / total_requests
            avg_response_time = self.metrics["total_response_time"] / total_requests
            cache_hit_rate = self.metrics["cache_hits"] / self.metrics.get("cache_requests", 1)
        else:
            success_rate = 0.0
            avg_response_time = 0.0
            cache_hit_rate = 0.0
            
        return {
            "service": self.service_name,
            "total_requests": total_requests,
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": round(success_rate, 4),
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "cache_hits": self.metrics["cache_hits"],
            "cache_hit_rate": round(cache_hit_rate, 4),
            "errors_by_type": self.metrics["errors_by_type"]
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for the service"""
        try:
            # Make a simple request to check connectivity
            # This should be overridden by subclasses with appropriate endpoint
            start_time = time.time()
            await self._make_request("GET", "/", use_cache=False)
            response_time = time.time() - start_time
            
            return {
                "service": self.service_name,
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2)
            }
        except Exception as e:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "error": str(e)
            }