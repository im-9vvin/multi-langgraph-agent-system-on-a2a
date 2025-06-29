"""Middleware stack for the server."""

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} for "
                f"{request.method} {request.url.path} "
                f"({duration:.3f}s)"
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error processing {request.method} {request.url.path}: "
                f"{str(e)} ({duration:.3f}s)"
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Handles errors gracefully."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            
            # Return JSON error response
            return Response(
                content={
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e) if logger.isEnabledFor(logging.DEBUG) else None
                    }
                },
                status_code=500,
                media_type="application/json"
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects basic metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            response = await call_next(request)
            
            if response.status_code >= 400:
                self.error_count += 1
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            # Add metrics headers
            response.headers["X-Request-Count"] = str(self.request_count)
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            self.error_count += 1
            duration = time.time() - start_time
            self.total_duration += duration
            raise
    
    def get_metrics(self) -> dict:
        """Get collected metrics.
        
        Returns:
            Metrics dictionary
        """
        avg_duration = (
            self.total_duration / self.request_count
            if self.request_count > 0
            else 0
        )
        
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / self.request_count
                if self.request_count > 0
                else 0
            ),
            "average_duration": avg_duration
        }