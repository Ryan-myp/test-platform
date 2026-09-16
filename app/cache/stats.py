"""Statistics caching layer"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger
from app.cache.redis import redis_client
from app.cache.decorators import cache


class StatsCache:
    """统计数据缓存"""
    
    # 缓存时间 (秒)
    DASHBOARD_TTL = 60      # 仪表盘 1分钟
    CASES_TTL = 120         # 用例列表 2分钟
    BUGS_TTL = 120          # Bug列表 2分钟
    
    def __init__(self):
        self._cache = {}  # 内存备用
    
    async def get_dashboard(self) -> Optional[Dict[str, Any]]:
        """获取仪表盘数据"""
        cache_key = "stats:dashboard"
        
        # 优先 Redis
        if redis_client.connected:
            data = await redis_client.get_json(cache_key)
            if data:
                return data
        
        # 降级到内存
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.now() < entry['expires']:
                return entry['data']
        
        return None
    
    async def set_dashboard(self, data: Dict[str, Any]):
        """设置仪表盘数据"""
        cache_key = "stats:dashboard"
        
        # Redis
        if redis_client.connected:
            await redis_client.set_json(cache_key, data, ex=self.DASHBOARD_TTL)
        
        # 内存
        self._cache[cache_key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=self.DASHBOARD_TTL)
        }
    
    async def invalidate_dashboard(self):
        """使仪表盘缓存失效"""
        cache_key = "stats:dashboard"
        
        if redis_client.connected:
            await redis_client.delete(cache_key)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
    
    async def get_cases(self, params: Dict) -> Optional[list]:
        """获取用例列表缓存"""
        cache_key = f"stats:cases:{hash(str(params))}"
        
        if redis_client.connected:
            data = await redis_client.get_json(cache_key)
            if data:
                return data
        
        return None
    
    async def set_cases(self, params: Dict, data: list):
        """设置用例列表缓存"""
        cache_key = f"stats:cases:{hash(str(params))}"
        
        if redis_client.connected:
            await redis_client.set_json(cache_key, data, ex=self.CASES_TTL)
        
        self._cache[cache_key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=self.CASES_TTL)
        }
    
    async def invalidate_all(self):
        """清除所有缓存"""
        self._cache.clear()
        
        if redis_client.connected:
            cursor = 0
            while True:
                cursor, keys = await redis_client._client.scan(cursor, match="stats:*", count=100)
                if keys:
                    await redis_client._client.delete(*keys)
                if cursor == 0:
                    break


# 单例
stats_cache = StatsCache()