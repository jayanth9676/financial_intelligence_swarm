"""Production hardening middleware for FastAPI.

Includes:
- Error handling with structured error responses
- Rate limiting
- Security headers
- Request logging
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from typing import Callable, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling with structured error responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.exception(f"Unhandled exception for {request.url.path}")
            
            # Determine error type and status code
            error_type = type(exc).__name__
            status_code = 500
            
            if "NotFound" in error_type or "404" in str(exc):
                status_code = 404
            elif "Validation" in error_type or "Pydantic" in error_type:
                status_code = 422
            elif "Permission" in error_type or "Authorization" in error_type:
                status_code = 403
            elif "Authentication" in error_type:
                status_code = 401
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "type": error_type,
                        "message": str(exc),
                        "path": str(request.url.path),
                        "method": request.method,
                    },
                    "status": "error",
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting."""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        self._cleanup_task = None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return True
        
        # Record this request
        self.requests[client_ip].append(now)
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "type": "RateLimitExceeded",
                        "message": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                    },
                    "status": "error",
                },
                headers={"Retry-After": "60"},
            )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Cache control for API responses
        if request.url.path.startswith("/api") or not request.url.path.endswith((".js", ".css", ".png", ".jpg")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing information."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log request (skip health checks for log noise reduction)
        if request.url.path != "/health":
            logger.info(
                f"{request.method} {request.url.path} "
                f"- Status: {response.status_code} "
                f"- Duration: {duration:.3f}s "
                f"- Client: {request.client.host if request.client else 'unknown'}"
            )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response


def setup_production_middleware(app: FastAPI, config: Dict[str, Any] = None):
    """Setup all production middleware on the FastAPI app.
    
    Args:
        app: FastAPI application instance
        config: Optional configuration dict with:
            - rate_limit: requests per minute (default: 100)
            - enable_rate_limit: whether to enable rate limiting (default: True)
            - enable_logging: whether to enable request logging (default: True)
    """
    config = config or {}
    
    # Add middleware in order (last added = first executed)
    
    # 1. Request logging (outermost - runs first)
    if config.get("enable_logging", True):
        app.add_middleware(RequestLoggingMiddleware)
    
    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Rate limiting
    if config.get("enable_rate_limit", True):
        rate_limit = config.get("rate_limit", 100)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)
    
    # 4. Error handling (innermost - catches errors from route handlers)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "service": "financial-intelligence-swarm",
            "version": "1.0.0",
        }
    
    logger.info("Production middleware configured")
