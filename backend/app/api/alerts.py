from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_db_session
from app.services.fault_detector import FaultDetectorService
from app.schemas import AlertResponse

router = APIRouter(prefix="/api/faults-and-alerts", tags=["Fault & Asset Health"])

@router.get("", response_model=List[AlertResponse])
async def get_alerts(session: AsyncSession = Depends(get_db_session)):
    alerts = await FaultDetectorService.get_active_alerts(session)
    return alerts
