"""Audit logging middleware"""
import logging
import uuid
import time
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """请求审计日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} | "
            f"IP: {self._get_client_ip(request)} | "
            f"User-Agent: {request.headers.get('user-agent', '')[:50]}"
        )
        
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000
            
            # 记录响应
            logger.info(
                f"[{request_id}] {response.status_code} | "
                f"Duration: {duration:.1f}ms"
            )
            
            # 添加请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.1f}ms"
            
            return response
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] ERROR | {str(e)[:100]} | "
                f"Duration: {duration:.1f}ms"
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
