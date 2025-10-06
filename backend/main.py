"""
BRANE Backend - FastAPI Application Entry Point
Privacy-first AI agent platform for healthcare/legal/finance
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging
import time
from typing import AsyncIterator

from api import auth, neurons, chat, rag, admin, tools
from core.config.settings import get_settings
from db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting BRANE backend...")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Create storage directories
    import os
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.AXON_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.MODELS_PATH, exist_ok=True)
    logger.info("✅ Storage directories created")

    logger.info(f"🧠 BRANE v{settings.APP_VERSION} ready on {settings.HOST}:{settings.PORT}")

    yield

    # Shutdown
    logger.info("👋 Shutting down BRANE backend...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Privacy-first AI agent orchestration platform",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests with timing"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info({
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    })

    return response


# Health Check Routes
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check (for k8s probes)"""
    from db.database import get_db

    try:
        # Test database connection
        async with get_db() as db:
            await db.execute("SELECT 1")

        return {
            "status": "ready",
            "database": "connected",
            "version": settings.APP_VERSION
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e)
        }, 503


# API Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(neurons.router, prefix="/api/neurons", tags=["Neurons"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(tools.router, prefix="/api", tags=["Tools"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Privacy-first AI agent orchestration platform",
        "docs": "/api/docs" if settings.DEBUG else None
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
