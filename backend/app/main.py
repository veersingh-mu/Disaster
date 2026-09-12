import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.auth.jwt import validate_jwt_configuration
from backend.app.auth.router import router as auth_router
from backend.app.errors import register_exception_handlers
from backend.app.logging import RequestIdLoggingMiddleware, setup_logging
from backend.app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from backend.app.routers import (
    ai_router,
    alerts_router,
    case_studies_router,
    dem_router,
    exports_router,
    scenarios_router,
)

# Configure structured JSON logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

# Validate cryptographic configuration
validate_jwt_configuration()

app = FastAPI(
    title="FloodPath API",
    description="Rapid Dam & Glacial Lake Breach Inundation Scenario Tool - SIH 2026 (PS 26161)",
    version="1.0.0",
)

# Register structured exception handlers
register_exception_handlers(app)

# Request ID and lifecycle tracking middleware
app.add_middleware(RequestIdLoggingMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware for simulation runs
app.add_middleware(RateLimitMiddleware)

# CORS configuration
allowed_origins_env = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
)
origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth_router)
app.include_router(scenarios_router)
app.include_router(case_studies_router)
app.include_router(dem_router)
app.include_router(exports_router)
app.include_router(alerts_router)
app.include_router(ai_router)


@app.get("/")
def read_root():
    return {
        "name": "FloodPath API",
        "description": "Rapid Dam & Glacial Lake Breach Inundation Scenario Tool",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
def health_check():
    """Trivial health check endpoint for container orchestrators and monitoring."""
    return {"status": "ok", "app": "FloodPath API", "version": "1.0.0"}
