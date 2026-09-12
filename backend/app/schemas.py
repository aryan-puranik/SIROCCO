from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Site Schemas
class SiteBase(BaseModel):
    id: str
    name: str
    type: str
    capacity_mw: float
    timezone: str
    location_name: str
    status: str
    current_generation_mw: float
    health_score: float
    metadata_json: Optional[str] = None

class SiteResponse(SiteBase):
    class Config:
        from_attributes = True

# Forecast Point Schema
class ForecastPoint(BaseModel):
    time: Any
    p10_mw: float
    p50_mw: float
    p90_mw: float
    actual_mw: Optional[float] = None
    physics_potential_mw: Optional[float] = None
    status_flag: Optional[str] = "NORMAL"
    flag_reason: Optional[str] = None
    mitigation_action: Optional[str] = None

class ForecastResponse(BaseModel):
    site_id: str
    site_name: str
    capacity_mw: float
    site_type: str
    horizon: str
    model_version: Optional[str] = "v2.0-physics-informed"
    summary: Dict[str, Any]
    mitigations: Optional[List[Dict[str, Any]]] = []
    data: List[ForecastPoint]

# Explainability Schema
class FeatureAttribution(BaseModel):
    feature: str
    importance: float
    impact_direction: str  # 'positive', 'negative', 'neutral'
    description: str

class ExplainabilityResponse(BaseModel):
    site_id: str
    site_name: str
    model_type: str
    top_features: List[FeatureAttribution]
    physics_insights: List[str]

# What-If Simulator Schema
class WhatIfRequest(BaseModel):
    domain: str = Field(default="solar", description="'solar' or 'wind'")
    # Solar params
    solar_capacity_mw: Optional[float] = 545.0
    panel_tilt_deg: Optional[float] = 30.0
    panel_azimuth_deg: Optional[float] = 180.0
    inverter_capacity_mw: Optional[float] = 545.0
    soiling_loss_pct: Optional[float] = 3.0
    # Backward compatibility
    panel_capacity_kwp: Optional[float] = None
    inverter_capacity_kw: Optional[float] = None
    # Wind params
    wind_capacity_mw: Optional[float] = 596.0
    hub_height_m: Optional[float] = 100.0
    pitch_offset_deg: Optional[float] = 0.0
    cut_in_speed_ms: Optional[float] = 3.0
    air_density_kg_m3: Optional[float] = 1.225
    derating_pct: Optional[float] = 0.0

class SimulatedInterval(BaseModel):
    time: str
    baseline_mw: Optional[float] = None
    simulated_mw: Optional[float] = None
    delta_mw: Optional[float] = None
    baseline_wh: Optional[float] = None
    simulated_wh: Optional[float] = None
    delta_wh: Optional[float] = None
    delta_pct: float

class WhatIfResponse(BaseModel):
    domain: Optional[str] = "solar"
    entity_name: Optional[str] = None
    baseline_params: Dict[str, Any]
    simulated_params: Dict[str, Any]
    total_baseline_mwh: Optional[float] = None
    total_simulated_mwh: Optional[float] = None
    delta_mwh: Optional[float] = None
    total_baseline_kwh: Optional[float] = None
    total_simulated_kwh: Optional[float] = None
    annual_estimated_delta_kwh: Optional[float] = None
    yield_change_pct: float
    intervals: List[SimulatedInterval]

# Alerts & Faults Schema
class AlertResponse(BaseModel):
    id: int
    site_id: str
    site_name: str
    alert_type: str
    severity: str
    message: str
    diagnostic_details: Optional[str] = None
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True

# Recommendations Schema
class RecommendationResponse(BaseModel):
    id: int
    site_id: str
    site_name: str
    recommendation_type: str
    action: str
    rationale: str
    confidence: float
    impact_mw: float
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Metrics Schema
class MetricResponse(BaseModel):
    model_name: str
    site_id: str
    metric_name: str
    metric_value: float
    target_value: Optional[float] = None
    status: str
    split_type: str

class PortfolioOverview(BaseModel):
    total_capacity_mw: float
    current_generation_mw: float
    capacity_factor_pct: float
    forecast_24h_peak_mw: float
    active_alerts_count: int
    fleet_health_score: float
    sites: List[SiteResponse]
