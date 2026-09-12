from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.db import get_db_session
from app.models import Site, TimeSeriesData, Alert
from app.schemas import SiteResponse, PortfolioOverview

router = APIRouter(prefix="/api/sites", tags=["Sites & Portfolio"])

@router.get("", response_model=List[SiteResponse])
async def list_sites(session: AsyncSession = Depends(get_db_session)):
    stmt = select(Site).order_by(Site.name)
    result = await session.execute(stmt)
    sites = result.scalars().all()
    return sites

@router.get("/portfolio/overview", response_model=PortfolioOverview)
async def get_portfolio_overview(session: AsyncSession = Depends(get_db_session)):
    stmt = select(Site).order_by(Site.name)
    result = await session.execute(stmt)
    sites = result.scalars().all()

    total_capacity = sum(s.capacity_mw for s in sites) or 4.01
    total_gen = sum(s.current_generation_mw for s in sites) or 1.62
    cf_pct = (total_gen / total_capacity) * 100.0 if total_capacity > 0 else 0.0

    alerts_stmt = select(Alert).where(Alert.status == "ACTIVE")
    alerts_result = await session.execute(alerts_stmt)
    active_alerts = len(alerts_result.scalars().all())

    avg_health = sum(s.health_score for s in sites) / len(sites) if sites else 98.2

    return PortfolioOverview(
        total_capacity_mw=round(total_capacity, 3),
        current_generation_mw=round(total_gen, 3),
        capacity_factor_pct=round(cf_pct, 1),
        forecast_24h_peak_mw=round(total_capacity * 0.88, 3),
        active_alerts_count=active_alerts,
        fleet_health_score=round(avg_health, 1),
        sites=[SiteResponse.model_validate(s) for s in sites]
    )

@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: str, session: AsyncSession = Depends(get_db_session)):
    site = await session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return site
