"""
KONQER API - Main FastAPI Application
Production-ready backend for 12 B2B SaaS services
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from contextlib import asynccontextmanager
import time
import logging

from routers import auth, user, services, admin, webhooks
from models.database import engine, Base
from config import settings

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'konqer_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'konqer_api_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

# Lifespan context manager (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Konqer API...")

    # Create database tables (if not exists)
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        # await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database connection established")

    logger.info("✅ Konqer API started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Konqer API...")
    await engine.dispose()
    logger.info("✅ Database connections closed")

# FastAPI app
app = FastAPI(
    title="Konqer API",
    description="Unified API for 12 B2B SaaS services",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# CORS middleware (Kinsta origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (security)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["api.konqer.app", "*.konqer.app"]
    )

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    response.headers["X-Process-Time"] = str(duration)

    return response

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )

# Health check endpoint (Kubernetes probes)
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for Kubernetes liveness/readiness probes
    """
    return {
        "status": "healthy",
        "service": "konqer-api",
        "version": "1.0.0"
    }

# Metrics endpoint (Prometheus scraping)
@app.get("/metrics", tags=["System"])
async def metrics():
    """
    Prometheus metrics endpoint
    """
    from fastapi.responses import Response
    return Response(generate_latest(), media_type="text/plain")

# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    API root - basic info
    """
    return {
        "service": "Konqer API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled"
    }

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(services.router, prefix="/services", tags=["Services"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Startup event logging
@app.on_event("startup")
async def startup_event():
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
