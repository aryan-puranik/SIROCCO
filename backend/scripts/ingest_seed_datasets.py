import os
import json
from datetime import datetime
import pandas as pd
import numpy as np
import pvlib
from sqlalchemy import delete

from app.config import RAW_DATA_DIR, WIND_NAMEPLATE_MW, SOLAR_OPENMETEO_CAPACITY_MW, SOLAR_ROOFTOP_CAPACITY_MW
from app.db import sync_engine, Base, sync_session_maker
from app.models import Site, TimeSeriesData

def run_ingestion():
    print("=" * 60)
    print("SIROCCO — Dataset Ingestion Pipeline")
    print("=" * 60)

    # Recreate tables
    Base.metadata.create_all(bind=sync_engine)

    with sync_session_maker() as session:
        # Seed Sites
        sites_data = [
            Site(
                id="wind-site-1",
                name="Wind Site — Location 1",
                type="wind",
                capacity_mw=WIND_NAMEPLATE_MW,
                timezone="UTC",
                location_name="North Sea Offshore Cluster A",
                status="operational",
                current_generation_mw=0.81,
                health_score=99.2,
                metadata_json=json.dumps({"nameplate_mw": WIND_NAMEPLATE_MW, "hub_height_m": 100, "rotor_diameter_m": 90})
            ),
            Site(
                id="wind-site-2",
                name="Wind Site — Location 2",
                type="wind",
                capacity_mw=WIND_NAMEPLATE_MW,
                timezone="UTC",
                location_name="Highland Ridge Wind Farm B",
                status="operational",
                current_generation_mw=0.50,
                health_score=97.8,
                metadata_json=json.dumps({"nameplate_mw": WIND_NAMEPLATE_MW, "hub_height_m": 100, "rotor_diameter_m": 90})
            ),
            Site(
                id="solar-openmeteo",
                name="Solar PV Plant — OpenMeteo Asset",
                type="solar",
                capacity_mw=SOLAR_OPENMETEO_CAPACITY_MW,
                timezone="UTC",
                location_name="Central Valley PV Array",
                status="operational",
                current_generation_mw=0.0038,
                health_score=98.5,
                metadata_json=json.dumps({"capacity_kwp": 5.1, "tracking": "fixed-tilt", "inverter_kw": 5.0})
            ),
            Site(
                id="solar-rooftop",
                name="Rooftop Solar — Demo Asset",
                type="solar_rooftop",
                capacity_mw=SOLAR_ROOFTOP_CAPACITY_MW,
                timezone="Asia/Kolkata",
                location_name="Gandhinagar Rooftop Solar Lab (Gujarat)",
                status="operational",
                current_generation_mw=0.0035,
                health_score=99.0,
                metadata_json=json.dumps({"capacity_kwp": 5.0, "tilt_deg": 20, "azimuth_deg": 0, "inverter_kw": 5.0, "lat": 23.0225, "lon": 72.5714})
            )
        ]

        # Merge sites
        for s in sites_data:
            session.merge(s)
        session.commit()
        print(f"Successfully seeded 4 platform sites.")

    # 1. Ingest Wind Location 1
    file_loc1 = RAW_DATA_DIR / "Location1.csv"
    if file_loc1.exists():
        print(f"\nIngesting Wind Location 1 from {file_loc1.name}...")
        df1 = pd.read_csv(file_loc1, parse_dates=["Time"])
        # For database performance, sample or insert full dataset
        df1_db = pd.DataFrame({
            "time": df1["Time"],
            "site_id": "wind-site-1",
            "generation_mw": df1["Power"] * WIND_NAMEPLATE_MW,
            "temperature_c": df1["temperature_2m"],
            "humidity_pct": df1["relativehumidity_2m"],
            "dewpoint_c": df1["dewpoint_2m"],
            "wind_speed_ms": df1["windspeed_10m"],
            "windspeed_100m_ms": df1["windspeed_100m"],
            "winddirection_10m_deg": df1["winddirection_10m"],
            "winddirection_100m_deg": df1["winddirection_100m"],
            "windgusts_10m_ms": df1["windgusts_10m"],
            "data_quality_flag": "valid"
        })
        df1_db.to_sql("time_series_data", con=sync_engine, if_exists="append", index=False, chunksize=5000)
        print(f"  Inserted {len(df1_db)} rows for Wind Location 1.")

    # 2. Ingest Wind Location 2
    file_loc2 = RAW_DATA_DIR / "Location2.csv"
    if file_loc2.exists():
        print(f"\nIngesting Wind Location 2 from {file_loc2.name}...")
        df2 = pd.read_csv(file_loc2, parse_dates=["Time"])
        df2_db = pd.DataFrame({
            "time": df2["Time"],
            "site_id": "wind-site-2",
            "generation_mw": df2["Power"] * WIND_NAMEPLATE_MW,
            "temperature_c": df2["temperature_2m"],
            "humidity_pct": df2["relativehumidity_2m"],
            "dewpoint_c": df2["dewpoint_2m"],
            "wind_speed_ms": df2["windspeed_10m"],
            "windspeed_100m_ms": df2["windspeed_100m"],
            "winddirection_10m_deg": df2["winddirection_10m"],
            "winddirection_100m_deg": df2["winddirection_100m"],
            "windgusts_10m_ms": df2["windgusts_10m"],
            "data_quality_flag": "valid"
        })
        df2_db.to_sql("time_series_data", con=sync_engine, if_exists="append", index=False, chunksize=5000)
        print(f"  Inserted {len(df2_db)} rows for Wind Location 2.")

    # 3. Ingest Solar PV OpenMeteo
    file_solar_pv = RAW_DATA_DIR / "pv-forecast-openmeteo-2020-2022-1h.csv"
    if file_solar_pv.exists():
        print(f"\nIngesting Solar OpenMeteo PV from {file_solar_pv.name}...")
        df_spv = pd.read_csv(file_solar_pv)
        df_spv_db = pd.DataFrame({
            "time": pd.to_datetime(df_spv["time"]),
            "site_id": "solar-openmeteo",
            "generation_mw": df_spv["avg W"] / 1_000_000.0,
            "temperature_c": df_spv["temp"] - 273.15,
            "humidity_pct": df_spv["humidity"].astype(float),
            "wind_speed_ms": df_spv["wind_speed"].astype(float),
            "winddirection_10m_deg": df_spv["wind_deg"].astype(float),
            "cloud_cover_total_pct": df_spv["clouds_all"].astype(float),
            "mslp_hpa": df_spv["pressure"].astype(float),
            "clearsky_w": df_spv["clear_sky"].astype(float),
            "data_quality_flag": "valid"
        })
        df_spv_db.to_sql("time_series_data", con=sync_engine, if_exists="append", index=False, chunksize=5000)
        print(f"  Inserted {len(df_spv_db)} rows for Solar OpenMeteo PV.")

    # 4. Ingest Solar Rooftop Demo
    file_rooftop = RAW_DATA_DIR / "solar_forecast.csv"
    if file_rooftop.exists():
        print(f"\nIngesting Solar Rooftop Demo from {file_rooftop.name}...")
        dfr = pd.read_csv(file_rooftop)
        timestamps = pd.to_datetime(dfr["timestamp"])
        solpos = pvlib.solarposition.get_solarposition(timestamps, 23.0225, 72.5714)

        avg_power_mw = (dfr["forecast_energy_wh_15min"] / 1000.0 / 0.25) / 1000.0

        dfr_db = pd.DataFrame({
            "time": timestamps,
            "site_id": "solar-rooftop",
            "generation_mw": avg_power_mw,
            "solar_zenith_deg": solpos["zenith"].values,
            "solar_azimuth_deg": solpos["azimuth"].values,
            "data_quality_flag": "sparse_features"
        })
        dfr_db.to_sql("time_series_data", con=sync_engine, if_exists="append", index=False, chunksize=5000)
        print(f"  Inserted {len(dfr_db)} rows for Solar Rooftop Demo.")

    print("\n" + "=" * 60)
    print("DATA INGESTION COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_ingestion()
