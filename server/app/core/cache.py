"""
Redis Cache Utility
Provides caching functionality for API responses with TTL support
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime
from urllib.parse import urlparse
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager with TTL support"""
    
    def __init__(self):
        """Initialize Redis connection"""
        if not settings.enable_caching:
            logger.info("Caching is disabled")
            self.redis_client = None
            self._connected = False
            return
            
        try:
            # Parse Redis URL if provided
            if settings.redis_url:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True
                )
            else:
                # Fallback to localhost for development
                self.redis_client = redis.Redis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=True
                )
            # Test connection
            self.redis_client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            self._connected = False
    
    def generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments"""
        parts = [prefix] + [str(arg).lower() for arg in args]
        return ":".join(parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client or not settings.enable_caching:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.info(f"Cache hit: {key}")
                return json.loads(value)
            logger.info(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL in seconds"""
        if not self.redis_client or not settings.enable_caching:
            return False
        
        try:
            json_value = json.dumps(value)
            self.redis_client.setex(key, ttl, json_value)
            logger.info(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client or not settings.enable_caching:
            return False
        
        try:
            result = self.redis_client.delete(key)
            if result:
                logger.info(f"Cache deleted: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client or not settings.enable_caching:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get remaining TTL for a key in seconds"""
        if not self.redis_client or not settings.enable_caching:
            return -1
        
        try:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl else -1
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return -1
    
    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.redis_client or not settings.enable_caching:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cache flush: {deleted} keys matching {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return 0


class CreditSpreadCache:
    """Specialized cache for credit spread analysis results"""
    
    def __init__(self):
        self.cache = RedisCache()
        self.prefix = "credit_spread"
        self.ttl = 60  # 60 seconds cache duration
    
    def get_spread_result(self, ticker: str, trend: str) -> Optional[Dict]:
        """Get cached credit spread result"""
        key = self.cache.generate_key(self.prefix, ticker, trend)
        cached_data = self.cache.get(key)
        
        if cached_data:
            # Add fresh timestamp and cache hit flag
            cached_data['timestamp'] = datetime.utcnow().isoformat()
            if 'market_context' in cached_data:
                cached_data['market_context']['cache_hit'] = True
            
            # Get remaining TTL
            ttl = self.cache.get_ttl(key)
            if ttl > 0:
                logger.info(f"Credit spread cache hit: {ticker} {trend} (expires in {ttl}s)")
            
            return cached_data
        
        return None
    
    def set_spread_result(self, ticker: str, trend: str, result: Dict) -> bool:
        """Cache credit spread result"""
        key = self.cache.generate_key(self.prefix, ticker, trend)
        success = self.cache.set(key, result, self.ttl)
        
        if success:
            logger.info(f"Credit spread cached: {ticker} {trend} (60s TTL)")
        
        return success
    
    def invalidate_ticker(self, ticker: str) -> int:
        """Invalidate all cache entries for a ticker"""
        pattern = f"{self.prefix}:{ticker.lower()}:*"
        deleted = self.cache.flush_pattern(pattern)
        
        if deleted:
            logger.info(f"Invalidated {deleted} cache entries for {ticker}")
        
        return deleted
    
    def clear_all(self) -> int:
        """Clear all credit spread cache entries"""
        pattern = f"{self.prefix}:*"
        deleted = self.cache.flush_pattern(pattern)
        
        if deleted:
            logger.info(f"Cleared {deleted} credit spread cache entries")
        
        return deleted


class CacheManager:
    """Cache manager with connection state tracking"""
    
    def __init__(self):
        self._connected = False
        self._cache = None
        
    @property
    def cache(self) -> RedisCache:
        """Get or create cache instance"""
        if self._cache is None:
            self._cache = RedisCache()
            self._connected = self._cache._connected
        return self._cache
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        if not self._connected:
            return {"status": "disconnected"}
        
        try:
            info = self.cache.redis_client.info()
            return {
                "status": "connected",
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"status": "error", "error": str(e)}
    
    async def disconnect(self):
        """Disconnect from cache"""
        if self._cache and self._cache.redis_client:
            try:
                await self._cache.redis_client.aclose()
            except:
                pass
        self._connected = False

# Global cache instances
cache_manager = CacheManager()
redis_cache = cache_manager.cache
credit_spread_cache = CreditSpreadCache()