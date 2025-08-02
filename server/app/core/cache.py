import json
import hashlib
import asyncio
from typing import Any, Callable, Optional, Union, Dict, List, TypeVar
from functools import wraps
from datetime import timedelta
import pickle
import redis.asyncio as redis
from redis.exceptions import RedisError

from .config import settings
from .logging import get_logger


logger = get_logger(__name__)

T = TypeVar('T')


class CacheManager:
    """
    Centralized caching system with:
    - Multiple cache backends (Redis, in-memory)
    - TTL management
    - Cache key generation
    - Cache invalidation strategies
    - Metrics and monitoring
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = settings.cache.default_ttl
        self.key_prefix = settings.cache.key_prefix
        self.namespace_separator = settings.cache.namespace_separator
        self._connected = False
        
        # Cache metrics
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "sets": 0,
            "deletes": 0
        }
        
    async def connect(self):
        """Connect to Redis"""
        if self._connected:
            return
            
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # We'll handle encoding/decoding
            )
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Redis cache connected", url=self.redis_url)
        except (RedisError, ConnectionError) as e:
            logger.error("Failed to connect to Redis", error=e)
            self.redis_client = None
            self._connected = False
            
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client and self._connected:
            await self.redis_client.close()
            self._connected = False
            logger.info("Redis cache disconnected")
            
    def _make_key(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> str:
        """Generate cache key with namespace and prefix"""
        parts = []
        
        # Add custom or default prefix
        if prefix:
            parts.append(prefix)
        elif self.key_prefix:
            parts.append(self.key_prefix)
            
        # Add namespace
        if namespace:
            parts.append(namespace)
            
        # Add the actual key
        parts.append(key)
        
        return self.namespace_separator.join(parts)
        
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
            
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
            
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error("Failed to deserialize cache data", error=e)
                return None
                
    def _get_ttl(self, ttl: Optional[int] = None, data_type: Optional[str] = None) -> int:
        """Get TTL based on provided value, data type, or default"""
        if ttl is not None:
            return min(ttl, settings.cache.max_ttl)
            
        if data_type and data_type in settings.cache.ttl_mapping:
            return settings.cache.ttl_mapping[data_type]
            
        return self.default_ttl
        
    async def get(
        self, 
        key: str,
        namespace: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """Get value from cache"""
        if not self._connected or not self.redis_client:
            self.metrics["errors"] += 1
            return default
            
        full_key = self._make_key(key, namespace)
        
        try:
            data = await self.redis_client.get(full_key)
            if data is None:
                self.metrics["misses"] += 1
                logger.log_cache_miss(full_key, namespace=namespace)
                return default
                
            self.metrics["hits"] += 1
            logger.log_cache_hit(full_key, namespace=namespace)
            return self._deserialize(data)
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache get error", error=e, key=full_key)
            return default
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        data_type: Optional[str] = None
    ) -> bool:
        """Set value in cache"""
        if not self._connected or not self.redis_client:
            self.metrics["errors"] += 1
            return False
            
        full_key = self._make_key(key, namespace)
        ttl_seconds = self._get_ttl(ttl, data_type)
        
        try:
            serialized = self._serialize(value)
            await self.redis_client.setex(
                full_key,
                ttl_seconds,
                serialized
            )
            self.metrics["sets"] += 1
            logger.debug("Cache set", key=full_key, ttl=ttl_seconds)
            return True
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache set error", error=e, key=full_key)
            return False
            
    async def get_or_set(
        self,
        key: str,
        func: Callable,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        data_type: Optional[str] = None
    ) -> Any:
        """Get from cache or execute function and cache result"""
        # Try to get from cache first
        cached = await self.get(key, namespace)
        if cached is not None:
            return cached
            
        # Execute function
        if asyncio.iscoroutinefunction(func):
            result = await func()
        else:
            result = func()
            
        # Cache the result
        if result is not None:
            await self.set(key, result, ttl, namespace, data_type)
            
        return result
        
    async def delete(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """Delete a key from cache"""
        if not self._connected or not self.redis_client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        try:
            result = await self.redis_client.delete(full_key)
            self.metrics["deletes"] += 1
            logger.debug("Cache delete", key=full_key, success=bool(result))
            return bool(result)
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache delete error", error=e, key=full_key)
            return False
            
    async def delete_pattern(
        self,
        pattern: str,
        namespace: Optional[str] = None
    ) -> int:
        """Delete all keys matching pattern"""
        if not self._connected or not self.redis_client:
            return 0
            
        full_pattern = self._make_key(pattern, namespace)
        
        try:
            # Use SCAN to find keys (more efficient than KEYS)
            deleted = 0
            cursor = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor,
                    match=full_pattern,
                    count=100
                )
                
                if keys:
                    deleted += await self.redis_client.delete(*keys)
                    
                if cursor == 0:
                    break
                    
            self.metrics["deletes"] += deleted
            logger.info("Cache pattern delete", pattern=full_pattern, deleted=deleted)
            return deleted
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache pattern delete error", error=e, pattern=full_pattern)
            return 0
            
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all cache in a namespace"""
        pattern = f"*"
        return await self.delete_pattern(pattern, namespace)
        
    async def exists(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """Check if key exists in cache"""
        if not self._connected or not self.redis_client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        try:
            return bool(await self.redis_client.exists(full_key))
        except Exception as e:
            logger.error("Cache exists error", error=e, key=full_key)
            return False
            
    async def get_many(
        self,
        keys: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self._connected or not self.redis_client:
            return {}
            
        full_keys = [self._make_key(k, namespace) for k in keys]
        
        try:
            values = await self.redis_client.mget(full_keys)
            result = {}
            
            for key, full_key, value in zip(keys, full_keys, values):
                if value is not None:
                    self.metrics["hits"] += 1
                    result[key] = self._deserialize(value)
                else:
                    self.metrics["misses"] += 1
                    
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache get_many error", error=e)
            return {}
            
    async def set_many(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """Set multiple values in cache"""
        if not self._connected or not self.redis_client:
            return False
            
        ttl_seconds = self._get_ttl(ttl)
        
        try:
            pipe = self.redis_client.pipeline()
            
            for key, value in data.items():
                full_key = self._make_key(key, namespace)
                serialized = self._serialize(value)
                pipe.setex(full_key, ttl_seconds, serialized)
                
            await pipe.execute()
            self.metrics["sets"] += len(data)
            return True
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Cache set_many error", error=e)
            return False
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 4),
            "connected": self._connected
        }


# Global cache manager instance
cache_manager = CacheManager()


# Cache key generation utilities
def generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    prefix: Optional[str] = None
) -> str:
    """Generate cache key from function and arguments"""
    # Create a unique key based on function name and arguments
    key_parts = [func.__module__, func.__name__]
    
    # Add args to key
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # For complex objects, use hash
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
            
    # Add kwargs to key (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        else:
            key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")
            
    # Join with separator
    base_key = ":".join(key_parts)
    
    # Add prefix if provided
    if prefix:
        return f"{prefix}:{base_key}"
        
    return base_key


# Cache decorator
def cache(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    namespace: Optional[str] = None,
    data_type: Optional[str] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Custom key prefix
        namespace: Cache namespace
        data_type: Data type for TTL mapping
        condition: Function to determine if result should be cached
        
    Example:
        @cache(ttl=600, namespace="market_data")
        async def get_stock_price(symbol: str):
            return await fetch_from_api(symbol)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if caching is enabled
            if not settings.features.get("enable_caching", True):
                return await func(*args, **kwargs)
                
            # Check condition
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)
                
            # Generate cache key
            cache_key = generate_cache_key(func, args, kwargs, key_prefix)
            
            # Try to get from cache
            cached = await cache_manager.get(cache_key, namespace)
            if cached is not None:
                return cached
                
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result if not None
            if result is not None:
                await cache_manager.set(
                    cache_key,
                    result,
                    ttl=ttl,
                    namespace=namespace,
                    data_type=data_type
                )
                
            return result
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    async_wrapper(*args, **kwargs)
                )
            finally:
                loop.close()
                
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# Cache invalidation decorator
def invalidate_cache(
    pattern: str,
    namespace: Optional[str] = None
):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        pattern: Cache key pattern to invalidate
        namespace: Cache namespace
        
    Example:
        @invalidate_cache("stock_price:*", namespace="market_data")
        async def update_stock_prices():
            # Update logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache_manager.delete_pattern(pattern, namespace)
            return result
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    cache_manager.delete_pattern(pattern, namespace)
                )
            finally:
                loop.close()
            return result
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator