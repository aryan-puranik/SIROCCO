from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import CORS_ORIGINS
from app.db import async_engine, Base
from app.api import sites, forecasts, explainability, simulator, alerts, decision, metrics

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created on startup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="SIROCCO API",
    description="AI-Powered Renewable Generation Forecasting, Grid Decision & Asset Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(sites.router)
app.include_router(forecasts.router)
app.include_router(explainability.router)
app.include_router(simulator.router)
app.include_router(alerts.router)
app.include_router(decision.router)
app.include_router(metrics.router)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

# Mount frontend build static files if built
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "platform": "SIROCCO — AI-Powered Renewable Generation Forecasting Platform",
            "status": "online",
            "docs_url": "/docs",
            "version": "1.0.0"
        }
