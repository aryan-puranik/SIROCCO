from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_db_session
from app.services.decision_engine import DecisionEngineService
from app.schemas import RecommendationResponse

router = APIRouter(prefix="/api/decision-engine", tags=["Grid Decision & Dispatch"])

@router.get("", response_model=List[RecommendationResponse])
async def get_grid_recommendations(session: AsyncSession = Depends(get_db_session)):
    recs = await DecisionEngineService.get_recommendations(session)
    return recs
