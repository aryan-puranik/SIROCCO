import pandas as pd
from fastapi import APIRouter, HTTPException
from app.config import DATA_DIR, RAW_DATA_DIR
from app.ml.simulator import FleetSolarSimulator, FleetWindSimulator
from app.schemas import WhatIfRequest, WhatIfResponse

router = APIRouter(prefix="/api/simulator", tags=["Digital Twin Simulator"])

# In-memory caches for fast slider responses
cached_solar_df = None
cached_wind_df = None

def get_solar_df():
    global cached_solar_df
    if cached_solar_df is None:
        p_path = DATA_DIR / "combined_solar.parquet"
        if p_path.exists():
            cached_solar_df = pd.read_parquet(p_path)
        else:
            csv_path = RAW_DATA_DIR / "solar_forecast.csv"
            cached_solar_df = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
    return cached_solar_df

def get_wind_df():
    global cached_wind_df
    if cached_wind_df is None:
        p_path = DATA_DIR / "combined_wind.parquet"
        if p_path.exists():
            cached_wind_df = pd.read_parquet(p_path)
        else:
            cached_wind_df = pd.DataFrame()
    return cached_wind_df

@router.post("/what-if", response_model=WhatIfResponse)
async def run_what_if_simulation(params: WhatIfRequest):
    domain = params.domain.lower()

    if domain == "wind":
        df = get_wind_df()
        if df.empty:
            raise HTTPException(status_code=500, detail="Wind fleet dataset not loaded.")
        simulator = FleetWindSimulator()
        result = simulator.simulate(
            time_series_df=df.tail(288),  # Last 3 days (72 hours)
            sim_capacity_mw=params.wind_capacity_mw or 596.0,
            sim_hub_height_m=params.hub_height_m or 100.0,
            sim_pitch_deg=params.pitch_offset_deg or 0.0,
            sim_cut_in_ms=params.cut_in_speed_ms or 3.0,
            sim_air_density=params.air_density_kg_m3 or 1.225,
            sim_derating_pct=params.derating_pct or 0.0
        )
        return result
    else:
        # Solar domain (default)
        df = get_solar_df()
        if df.empty:
            raise HTTPException(status_code=500, detail="Solar fleet dataset not loaded.")
        simulator = FleetSolarSimulator()
        cap = params.solar_capacity_mw or (params.panel_capacity_kwp * 0.001 if params.panel_capacity_kwp else 545.0)
        inv = params.inverter_capacity_mw or (params.inverter_capacity_kw * 0.001 if params.inverter_capacity_kw else cap)
        result = simulator.simulate(
            time_series_df=df.tail(288),  # Last 3 days (72 hours)
            sim_capacity_mw=cap,
            sim_tilt=params.panel_tilt_deg if params.panel_tilt_deg is not None else 30.0,
            sim_azimuth=params.panel_azimuth_deg if params.panel_azimuth_deg is not None else 180.0,
            sim_inverter_mw=inv,
            sim_soiling_pct=params.soiling_loss_pct if params.soiling_loss_pct is not None else 3.0
        )
        return result
