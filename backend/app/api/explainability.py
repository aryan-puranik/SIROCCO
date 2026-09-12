from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db_session
from app.models import Site
from app.ml.explainability import ExplainabilityEngine
from app.schemas import ExplainabilityResponse

router = APIRouter(prefix="/api/explainability", tags=["Explainability"])

@router.get("/{site_id}", response_model=ExplainabilityResponse)
async def get_explainability(site_id: str, session: AsyncSession = Depends(get_db_session)):
    site = await session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")

    data = ExplainabilityEngine.get_site_explanations(site.type, site.id)
    return ExplainabilityResponse(
        site_id=site.id,
        site_name=site.name,
        model_type=data["model_type"],
        top_features=data["top_features"],
        physics_insights=data["physics_insights"]
    )
