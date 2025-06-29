"""Main application factory for the orchestrator agent server."""

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from ..common.config import config
from .middleware import ErrorHandlingMiddleware, LoggingMiddleware
from .routes import routes


def create_app() -> Starlette:
    """Create the Starlette application."""
    app = Starlette(routes=routes)
    
    # Add middleware in reverse order (last added is first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    return app