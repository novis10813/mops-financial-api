"""
MOPS Financial API - FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import financial, xbrl, analysis, revenue

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup: Initialize taxonomies
    try:
        from app.services.taxonomy_manager import init_taxonomies
        await init_taxonomies()
        logger.info("Taxonomy initialization complete")
    except Exception as e:
        logger.warning(f"Failed to initialize taxonomies: {e}")
        logger.warning("Application will use fallback schema mappings")
    
    # Startup: Initialize database
    try:
        from app.db import init_db
        await init_db()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.warning(f"Failed to initialize database: {e}")
        logger.warning("Database features will be unavailable")
    
    yield
    
    # Shutdown: Close database connection
    try:
        from app.db import close_db
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")
    
    logger.info("Application shutting down")


app = FastAPI(
    title="MOPS Financial API",
    description="REST API for Taiwan MOPS financial reports with XBRL parsing",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(financial.router, prefix="/api/v1/financial", tags=["financial"])
app.include_router(xbrl.router, prefix="/api/v1/xbrl", tags=["xbrl"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(revenue.router, prefix="/api/v1", tags=["revenue"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "mops-financial-api"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

