"""Redis-based rate limiting store"""
import time
from typing import Dict, List
from loguru import logger
from app.cache.redis import redis_client


class RateLimitStore:
    """基于 Redis 的速率限制存储"""
    
    def __init__(self):
        self._store: Dict[str, List[float]] = {}  # 内存备用
    
    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - window_seconds
        
        if redis_client.connected:
            # Redis 实现
            pipe = redis_client._client.pipeline()
            pipe.multi()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, '-inf', window_start)
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = pipe.execute()
            current_count = results[2]
        else:
            # 内存实现
            if key not in self._store:
                self._store[key] = []
            
            # 清理过期记录
            self._store[key] = [t for t in self._store[key] if t > window_start]
            current_count = len(self._store[key])
            
            if current_count < max_requests:
                self._store[key].append(now)
        
        return current_count < max_requests
    
    async def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """获取剩余请求数"""
        now = time.time()
        window_start = now - window_seconds
        
        if redis_client.connected:
            pipe = redis_client._client.pipeline()
            pipe.zcount(key, window_start, '+inf')
            pipe.ttl(key)
            results = pipe.execute()
            current_count = results[0]
        else:
            if key not in self._store:
                return max_requests
            nows = [t for t in self._store[key] if t > window_start]
            current_count = len(nows)
        
        return max(0, max_requests - current_count)
    
    async def reset(self, key: str):
        """重置限制"""
        if redis_client.connected:
            await redis_client.delete(key)
        elif key in self._store:
            del self._store[key]