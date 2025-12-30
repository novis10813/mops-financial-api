"""
MOPS Financial API - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import financial, xbrl, analysis

app = FastAPI(
    title="MOPS Financial API",
    description="REST API for Taiwan MOPS financial reports with XBRL parsing",
    version="0.1.0",
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "mops-financial-api"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
