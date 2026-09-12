from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.power_management import PowerManagementService

class ForecastService:
    """
    Produces multi-horizon forecasts with P10, P50, and P90 confidence intervals,
    statistical over/under capacity detection, and physics-informed predictive maintenance.
    """

    @staticmethod
    async def get_forecast_for_site(
        session: AsyncSession,
        site_id: str,
        horizon: str = "48h"
    ) -> Dict[str, Any]:
        return await PowerManagementService.get_fleet_power_forecast(session, site_id, horizon)
