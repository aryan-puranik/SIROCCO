from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db_session
from app.services.forecast_service import ForecastService
from app.schemas import ForecastResponse

router = APIRouter(prefix="/api/forecasts", tags=["Forecasting & Power Management"])

@router.get("/{site_id}", response_model=ForecastResponse)
async def get_site_forecast(
    site_id: str,
    horizon: str = Query(default="48h", regex="^(24h|48h|72h|7d)$"),
    session: AsyncSession = Depends(get_db_session)
):
    try:
        data = await ForecastService.get_forecast_for_site(session, site_id, horizon)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")
