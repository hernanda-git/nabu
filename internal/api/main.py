"""
𒀭 NABU — FastAPI Application Factory
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nabu.api.routes import opportunities, wallets, machines, events, analytics
from nabu.api.auth import auth_middleware
from nabu.api.middleware import rate_limit_middleware, logging_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup/shutdown."""
    # Startup
    print("𒀭 Nabu API starting...")
    # Initialize DB pool, Redis, etc.
    yield
    # Shutdown
    print("𒀭 Nabu API shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nabu — Airdrop Intelligence Cortex",
        version="3.0.0",
        description="The Oracle's API — Real-time airdrop intelligence for mining machines",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware
    app.middleware("http")(logging_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(auth_middleware)

    # Routes
    app.include_router(opportunities.router, prefix="/api/v1")
    app.include_router(wallets.router, prefix="/api/v1")
    app.include_router(machines.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")

    # Health
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "nabu-api", "version": "3.0.0"}

    @app.get("/ready")
    async def ready():
        # Check DB, Redis, RabbitMQ
        return {"ready": True}

    # Error handlers
    @app.exception_handler(404)
    async def not_found(request, exc):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    @app.exception_handler(500)
    async def server_error(request, exc):
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "nabu.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8443")),
        reload=os.getenv("ENV") == "development",
    )