"""Rate limiting middleware"""
import time
import logging
from collections import defaultdict
from typing import Dict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 内存存储请求计数
_request_counts: Dict[str, list] = defaultdict(list)

# 默认速率限制配置
DEFAULT_LIMITS = {
    "general": {"requests": 100, "window": 60},      # 100 requests/minute
    "auth": {"requests": 5, "window": 60},           # 5 login attempts/minute
    "api": {"requests": 30, "window": 60},           # 30 API calls/minute
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的速率限制中间件"""
    
    def __init__(self, app, limits: Dict[str, Dict] = None):
        super().__init__(app)
        self.limits = limits or DEFAULT_LIMITS
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 确定路径类别
        path = request.url.path
        category = self._get_category(path)
        
        # 检查速率限制
        limit_config = self.limits.get(category, self.limits["general"])
        max_requests = limit_config["requests"]
        window_seconds = limit_config["window"]
        
        now = time.time()
        timestamps = _request_counts[client_ip]
        
        # 清理过期记录
        cutoff = now - window_seconds
        _request_counts[client_ip] = [t for t in timestamps if t > cutoff]
        timestamps = _request_counts[client_ip]
        
        if len(timestamps) >= max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {window_seconds} seconds."
            )
        
        # 记录请求
        timestamps.append(now)
        
        response = await call_next(request)
        
        # 添加速率限制头
        remaining = max(0, max_requests - len(timestamps))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_category(self, path: str) -> str:
        """确定路径类别"""
        if path.startswith("/api/auth/"):
            return "auth"
        elif path.startswith("/api/"):
            return "api"
        return "general"
