import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    LoggingMiddleware: intercepts requests and logs processing time.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logging.info(f"API request {request.url.path} processed in {process_time:.4f}s")
        return response
