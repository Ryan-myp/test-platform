"""Redis client singleton"""
import redis.asyncio as aioredis
from typing import Optional
from loguru import logger
from app.config import settings


class RedisClient:
    """Redis 异步客户端"""
    
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """连接 Redis"""
        if settings.redis_url:
            try:
                self._client = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                await self._client.ping()
                self._connected = True
                logger.info("✅ Redis connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
                self._connected = False
        else:
            logger.info("ℹ️ Redis not configured, using in-memory cache")
            self._connected = False
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("🔌 Redis disconnected")
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._connected:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.opt(exception=e).debug(f"Redis GET failed: {key}")
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """设置值"""
        if not self._connected:
            return False
        try:
            await self._client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.opt(exception=e).debug(f"Redis SET failed: {key}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除"""
        if not self._connected:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.opt(exception=e).debug(f"Redis DELETE failed: {key}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """递增"""
        if not self._connected:
            return 0
        try:
            return await self._client.incr(key, amount)
        except Exception as e:
            logger.opt(exception=e).debug(f"Redis INCR failed: {key}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self._connected:
            return False
        try:
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.opt(exception=e).debug(f"Redis EXPIRE failed: {key}")
            return False
    
    async def set_json(self, key: str, value: dict, ex: Optional[int] = None):
        """设置 JSON 值"""
        import json
        await self.set(key, json.dumps(value, default=str), ex=ex)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """获取 JSON 值"""
        import json
        data = await self.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None


# 单例
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """获取 Redis 客户端"""
    return redis_client