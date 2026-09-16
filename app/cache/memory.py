"""Memory-based cache with TTL support"""
import time
import hashlib
import json
import functools
from typing import Any, Optional, Dict
from loguru import logger


class MemoryCache:
    """内存缓存，支持 TTL"""
    
    def __init__(self):
        self._store: Dict[str, dict] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._store:
            entry = self._store[key]
            if time.time() < entry['expires']:
                return entry['data']
            del self._store[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        self._store[key] = {
            'data': value,
            'expires': time.time() + ttl
        }
    
    def delete(self, key: str):
        """删除缓存"""
        self._store.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        self._store.clear()
    
    def stats(self) -> dict:
        """统计信息"""
        return {
            'size': len(self._store),
            'keys': list(self._store.keys())[:10]
        }


# 全局单例
_cache = MemoryCache()


def cache(ttl: int = 300, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            key_data = f"{key_prefix}:{func.__name__}:{json.dumps({'args': args, 'kwargs': kwargs}, default=str, sort_keys=True)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()[:16]
            
            # 尝试获取缓存
            cached = _cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            _cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            
            return result
        return wrapper
    return decorator
