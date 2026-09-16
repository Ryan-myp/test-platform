"""Custom exceptions and error handlers"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, "BAD_REQUEST", 400)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, "FORBIDDEN", 403)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, "CONFLICT", 409)


class RateLimitException(AppException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMITED", 429)


def register_exceptions(app: FastAPI):
    """注册异常处理器"""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(f"App exception: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "errors": [{"code": exc.code, "message": exc.message}],
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation error",
                "errors": exc.errors(),
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Database error",
                "errors": [{"code": "DB_ERROR", "message": "Internal database error"}],
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "errors": [{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}],
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        )
