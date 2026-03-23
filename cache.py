import time
import logging
from functools import wraps

logger = logging.getLogger("off-grid-api.cache")


class SimpleCache:
    """Simple in-memory TTL cache for API responses.

    Prevents redundant external API calls for the same coordinates.
    Cache entries expire after `ttl` seconds (default 1 hour).
    """

    def __init__(self, ttl=3600, max_size=500):
        self._store = {}
        self.ttl = ttl
        self.max_size = max_size

    def _make_key(self, prefix, *args, **kwargs):
        """Create a hashable cache key from function arguments."""
        key_parts = [prefix] + [str(a) for a in args]
        key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return ":".join(key_parts)

    def get(self, key):
        """Get a value from cache. Returns None if expired or missing."""
        if key in self._store:
            value, timestamp = self._store[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                del self._store[key]
                logger.debug(f"Cache EXPIRED: {key}")
        return None

    def set(self, key, value):
        """Set a value in cache with current timestamp."""
        # Evict oldest entries if at capacity
        if len(self._store) >= self.max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]
            logger.debug(f"Cache EVICTED: {oldest_key}")

        self._store[key] = (value, time.time())
        logger.debug(f"Cache SET: {key}")

    def clear(self):
        """Clear all cached entries."""
        self._store.clear()
        logger.info("Cache cleared")

    @property
    def size(self):
        return len(self._store)


# Global cache instance shared across modules
api_cache = SimpleCache(ttl=3600, max_size=500)


def cached(prefix):
    """Decorator to cache function results based on arguments.

    Usage:
        @cached("energy")
        def get_energy_data(lat, lon):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip 'self' argument for methods
            cache_args = args[1:] if args and hasattr(args[0], '__class__') else args
            key = api_cache._make_key(prefix, *cache_args, **kwargs)

            result = api_cache.get(key)
            if result is not None:
                logger.info(f"Using cached {prefix} data")
                return result

            result = func(*args, **kwargs)
            if result is not None:  # Only cache successful results
                api_cache.set(key, result)
            return result
        return wrapper
    return decorator
