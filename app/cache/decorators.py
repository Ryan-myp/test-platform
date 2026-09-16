"""Caching decorators"""
import hashlib
import functools
import json
from typing import Optional, Any, Callable
from loguru import logger
from app.cache.redis import redis_client


def cache_key(func: Callable, *args, **kwargs) -> str:
    """生成缓存键"""
    key_data = f"{func.__name__}:{json.dumps({'args': args, 'kwargs': kwargs}, default=str, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()[:16]


def cache(ttl: int = 300, key_prefix: str = "cache"):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client.connected:
                return await func(*args, **kwargs)
            
            cache_key_str = f"{key_prefix}:{cache_key(func, *args, **kwargs)}"
            
            # 尝试从缓存获取
            cached = await redis_client.get_json(cache_key_str)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            await redis_client.set_json(cache_key_str, result, ex=ttl)
            logger.debug(f"Cache set: {cache_key_str} (TTL: {ttl}s)")
            
            return result
        return wrapper
    return decorator


def cache_invalidate(func: Callable):
    """缓存失效装饰器（用于写操作）"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        # 清除相关缓存
        if redis_client.connected:
            prefix = kwargs.get('prefix', 'cache')
            # 模糊匹配清除
            pattern = f"{prefix}:*"
            cursor = 0
            while True:
                cursor, keys = await redis_client._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis_client._client.delete(*keys)
                if cursor == 0:
                    break
        
        return result
    return wrapper