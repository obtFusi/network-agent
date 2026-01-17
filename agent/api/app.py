# FastAPI Application Factory
"""Creates and configures the FastAPI application for Network Agent."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.api.config import APIConfig
from agent.api.middleware import RequestIDMiddleware, TimingMiddleware
from agent.api.middleware.error_handler import global_exception_handler
from agent.api.routers import chat, health, sessions
from agent.api.services.session_store import SessionStore

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting Network Agent API")
    app.state.session_store = SessionStore(
        config=app.state.config,
        system_prompt=app.state.system_prompt,
    )
    logger.info("Session store initialized")

    yield

    # Shutdown
    count = app.state.session_store.clear_all()
    logger.info("Shutdown complete", sessions_cleared=count)


def create_app(
    config: dict,
    system_prompt: str,
    api_config: APIConfig | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Agent configuration dictionary
        system_prompt: System prompt for the agent
        api_config: Optional API configuration

    Returns:
        Configured FastAPI application
    """
    if api_config is None:
        api_config = APIConfig()

    app = FastAPI(
        title="Network Agent API",
        description="AI-powered network scanning and reconnaissance agent",
        version=config.get("version", "0.8.0"),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Store config in app state
    app.state.config = config
    app.state.system_prompt = system_prompt
    app.state.api_config = api_config

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.cors.allow_origins,
        allow_credentials=api_config.cors.allow_credentials,
        allow_methods=api_config.cors.allow_methods,
        allow_headers=api_config.cors.allow_headers,
    )

    # Add custom middleware
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Add global exception handler
    app.add_exception_handler(Exception, global_exception_handler)

    # Include routers
    app.include_router(health.router)
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")

    return app
