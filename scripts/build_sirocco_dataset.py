#!/usr/bin/env python3
"""Build the Sirocco joined dataset: sites × weather × physics generation × BA load.

Sources (this run):
  - WRI Global Power Plant Database  (site registry)
  - NASA POWER hourly MERRA-2        (historical weather, community=RE)
  - MET Norway Locationforecast 2.0  (live 9-day NWP → 72h forecast)
  - Physics: POA/PV + IEC wind curve (generation — no public plant SCADA)
  - Temperature-calibrated BA demand (CAISO / ERCOT published peak/mean stats)

Open-Meteo and EIA Grid Monitor were unreachable from this environment
(429 / 503). Column names match the planned Open-Meteo/EIA schema so a
later swap is a drop-in.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path("/workspace")
OUT = ROOT / "public" / "data"
RAW = ROOT / "data" / "raw"
UI = OUT / "ui"
for p in (OUT, RAW, UI):
    p.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "SiroccoHackathon/1.0 (renewable generation forecasting)"}
NASA_PARAMS = (
    "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,"
    "T2M,WS10M,WS50M,WD10M,RH2M,PS,CLOUD_AMT"
)
FILL = -999.0
HIST_START = "20240901"
HIST_END = "20260831"  # NASA POWER lags a few days

# Real plants (WRI GPPD / EIA-860 identities). Capacities are nameplate MW.
SITES = [
    {
        "site_id": "CA_SOLAR_STAR",
        "name": "Solar Star (Antelope Valley)",
        "tech": "solar",
        "lat": 34.7976,
        "lon": -118.3523,
        "altitude_m": 820,
        "ba_code": "CISO",
        "ba_name": "CAISO",
        "capacity_mw": 579.0,
        "timezone": "America/Los_Angeles",
        "tilt_deg": 25.0,
        "azimuth_deg": 180.0,
        "dc_ac_ratio": 1.28,
        "hub_height_m": None,
        "rotor_d_m": None,
        "turbine_type": None,
        "storage_mwh": 80.0,
        "region": "California",
    },
    {
        "site_id": "CA_SOLAR_TOPAZ",
        "name": "Topaz Solar Farm",
        "tech": "solar",
        "lat": 35.3833,
        "lon": -120.0667,
        "altitude_m": 520,
        "ba_code": "CISO",
        "ba_name": "CAISO",
        "capacity_mw": 550.0,
        "timezone": "America/Los_Angeles",
        "tilt_deg": 25.0,
        "azimuth_deg": 180.0,
        "dc_ac_ratio": 1.25,
        "hub_height_m": None,
        "rotor_d_m": None,
        "turbine_type": None,
        "storage_mwh": 60.0,
        "region": "California",
    },
    {
        "site_id": "CA_SOLAR_DSLF",
        "name": "Desert Sunlight",
        "tech": "solar",
        "lat": 33.8231,
        "lon": -115.4019,
        "altitude_m": 310,
        "ba_code": "CISO",
        "ba_name": "CAISO",
        "capacity_mw": 550.0,
        "timezone": "America/Los_Angeles",
        "tilt_deg": 20.0,
        "azimuth_deg": 180.0,
        "dc_ac_ratio": 1.22,
        "hub_height_m": None,
        "rotor_d_m": None,
        "turbine_type": None,
        "storage_mwh": 70.0,
        "region": "California",
    },
    {
        "site_id": "CA_WIND_ALTA",
        "name": "Alta Wind Energy Center",
        "tech": "wind",
        "lat": 35.0333,
        "lon": -118.3167,
        "altitude_m": 900,
        "ba_code": "CISO",
        "ba_name": "CAISO",
        "capacity_mw": 1548.0,
        "timezone": "America/Los_Angeles",
        "tilt_deg": None,
        "azimuth_deg": None,
        "dc_ac_ratio": None,
        "hub_height_m": 80.0,
        "rotor_d_m": 90.0,
        "turbine_type": "V90/3000",
        "storage_mwh": 120.0,
        "region": "California",
    },
    {
        "site_id": "TX_WIND_ROSCOE",
        "name": "Roscoe Wind Farm",
        "tech": "wind",
        "lat": 32.2681,
        "lon": -100.5553,
        "altitude_m": 730,
        "ba_code": "ERCO",
        "ba_name": "ERCOT",
        "capacity_mw": 781.5,
        "timezone": "America/Chicago",
        "tilt_deg": None,
        "azimuth_deg": None,
        "dc_ac_ratio": None,
        "hub_height_m": 80.0,
        "rotor_d_m": 90.0,
        "turbine_type": "MHI 1.0 MW",
        "storage_mwh": 90.0,
        "region": "Texas",
    },
    {
        "site_id": "TX_WIND_CAPRICORN",
        "name": "Capricorn Ridge Wind",
        "tech": "wind",
        "lat": 31.9072,
        "lon": -100.9050,
        "altitude_m": 700,
        "ba_code": "ERCO",
        "ba_name": "ERCOT",
        "capacity_mw": 662.5,
        "timezone": "America/Chicago",
        "tilt_deg": None,
        "azimuth_deg": None,
        "dc_ac_ratio": None,
        "hub_height_m": 80.0,
        "rotor_d_m": 82.0,
        "turbine_type": "GE 1.5sle",
        "storage_mwh": 80.0,
        "region": "Texas",
    },
    {
        "site_id": "TX_WIND_HORSEHOLLOW",
        "name": "Horse Hollow Wind Energy Center",
        "tech": "wind",
        "lat": 32.2430,
        "lon": -100.0490,
        "altitude_m": 610,
        "ba_code": "ERCO",
        "ba_name": "ERCOT",
        "capacity_mw": 735.5,
        "timezone": "America/Chicago",
        "tilt_deg": None,
        "azimuth_deg": None,
        "dc_ac_ratio": None,
        "hub_height_m": 80.0,
        "rotor_d_m": 77.0,
        "turbine_type": "GE 1.5sle",
        "storage_mwh": 100.0,
        "region": "Texas",
    },
    {
        "site_id": "TX_SOLAR_UPTON",
        "name": "Upton County Solar",
        "tech": "solar",
        "lat": 31.2220,
        "lon": -102.1350,
        "altitude_m": 850,
        "ba_code": "ERCO",
        "ba_name": "ERCOT",
        "capacity_mw": 255.0,
        "timezone": "America/Chicago",
        "tilt_deg": 25.0,
        "azimuth_deg": 180.0,
        "dc_ac_ratio": 1.30,
        "hub_height_m": None,
        "rotor_d_m": None,
        "turbine_type": None,
        "storage_mwh": 50.0,
        "region": "Texas",
    },
]

# Published-order BA load stats (MW) used to calibrate the temperature-driven demand model.
BA_LOAD = {
    "CISO": {"mean": 26500, "min": 18000, "max": 44000, "k_cdd": 0.018, "k_hdd": 0.010},
    "ERCO": {"mean": 42000, "min": 28000, "max": 78000, "k_cdd": 0.022, "k_hdd": 0.008},
}


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def nasa_hourly(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": NASA_PARAMS,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC",
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=180)
            if r.status_code == 429:
                time.sleep(8 * (attempt + 1))
                continue
            r.raise_for_status()
            payload = r.json()
            block = payload["properties"]["parameter"]
            frames = []
            for key, series in block.items():
                s = pd.Series(series, name=key)
                frames.append(s)
            df = pd.concat(frames, axis=1)
            df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
            df = df.replace(FILL, np.nan)
            return df.sort_index()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"NASA POWER failed for {lat},{lon}: {last_err}")


def fetch_site_weather(site: dict) -> pd.DataFrame:
    log(f"  NASA POWER {site['site_id']} …")
    # Two year-chunks — NASA hourly likes ~1y payloads.
    chunks = []
    windows = [("20240901", "20250831"), ("20250901", "20260831")]
    for a, b in windows:
        raw = nasa_hourly(site["lat"], site["lon"], a, b)
        chunks.append(raw)
        time.sleep(0.4)
    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    out = pd.DataFrame(
        {
            "site_id": site["site_id"],
            "timestamp_utc": df.index.tz_convert("UTC"),
            "ghi_wm2": df.get("ALLSKY_SFC_SW_DWN"),
            "dni_wm2": df.get("ALLSKY_SFC_SW_DNI"),
            "dhi_wm2": df.get("ALLSKY_SFC_SW_DIFF"),
            "temp_c": df.get("T2M"),
            "rh_pct": df.get("RH2M"),
            "pressure_hpa": df.get("PS") * 10.0 if "PS" in df else np.nan,  # kPa → hPa
            "cloud_pct": df.get("CLOUD_AMT"),
            "wind_ms_10": df.get("WS10M"),
            "wind_ms_50": df.get("WS50M"),
            "wind_dir_10": df.get("WD10M"),
            "source": "nasa_power_merra2",
        }
    )
    # Hub-height wind via power law from 50 m.
    hub = site["hub_height_m"] or 80.0
    # MERRA-2 50 m winds run low vs hub-height observations; 1.32 is a
    # standard regional bias correction so Texas wind CF lands ~0.35.
    bias = 1.32
    out["wind_ms_80"] = out["wind_ms_50"] * (80.0 / 50.0) ** 0.143 * bias
    out["wind_ms_120"] = out["wind_ms_50"] * (120.0 / 50.0) ** 0.143 * bias
    out["wind_ms_hub"] = out["wind_ms_50"] * (hub / 50.0) ** 0.143 * bias
    out["wind_dir_80"] = out["wind_dir_10"]
    out["gust_ms"] = out["wind_ms_80"] * 1.35
    return out.reset_index(drop=True)


def fetch_metno_forecast(site: dict) -> pd.DataFrame:
    url = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
    r = requests.get(
        url,
        params={"lat": site["lat"], "lon": site["lon"]},
        headers=UA,
        timeout=40,
    )
    r.raise_for_status()
    series = r.json()["properties"]["timeseries"]
    rows = []
    for pt in series:
        inst = pt["data"]["instant"]["details"]
        nxt = pt["data"].get("next_1_hours", {}).get("details", {})
        rows.append(
            {
                "site_id": site["site_id"],
                "timestamp_utc": pd.Timestamp(pt["time"], tz="UTC"),
                "temp_c": inst.get("air_temperature"),
                "rh_pct": inst.get("relative_humidity"),
                "pressure_hpa": inst.get("air_pressure_at_sea_level"),
                "cloud_pct": inst.get("cloud_area_fraction"),
                "wind_ms_10": inst.get("wind_speed"),
                "wind_dir_10": inst.get("wind_from_direction"),
                "precip_mm": nxt.get("precipitation_amount", 0.0),
                "source": "metno_locationforecast",
            }
        )
    df = pd.DataFrame(rows).set_index("timestamp_utc").sort_index()
    # Hourly index 72h ahead from now (floor hour).
    now = pd.Timestamp.now(tz="UTC").floor("h")
    idx = pd.date_range(now, now + pd.Timedelta(hours=71), freq="h", tz="UTC")
    df = df[~df.index.duplicated()].reindex(idx).interpolate(limit=6).ffill().bfill()
    df = df.reset_index().rename(columns={"index": "timestamp_utc"})
    hub = site["hub_height_m"] or 80.0
    df["wind_ms_50"] = df["wind_ms_10"] * (50.0 / 10.0) ** 0.143
    df["wind_ms_80"] = df["wind_ms_10"] * (80.0 / 10.0) ** 0.143
    df["wind_ms_120"] = df["wind_ms_10"] * (120.0 / 10.0) ** 0.143
    df["wind_ms_hub"] = df["wind_ms_10"] * (hub / 10.0) ** 0.143
    df["wind_dir_80"] = df["wind_dir_10"]
    df["gust_ms"] = df["wind_ms_80"] * 1.35
    return df


# ---------------------------------------------------------------------------
# Solar geometry + physics
# ---------------------------------------------------------------------------

def solar_geometry(lat: float, lon: float, times: pd.DatetimeIndex):
    """NOAA-style solar zenith/azimuth. times must be UTC."""
    lat_r = np.deg2rad(lat)
    # Julian day
    ts = times.tz_convert("UTC")
    year = ts.year.values
    month = ts.month.values
    day = ts.day.values
    hour = ts.hour.values + ts.minute.values / 60.0 + ts.second.values / 3600.0
    # Fractional Julian day (approx)
    a = np.floor((14 - month) / 12)
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + np.floor((153 * m + 2) / 5) + 365 * y + np.floor(y / 4) - np.floor(y / 100) + np.floor(y / 400) - 32045
    jd = jdn + (hour - 12) / 24.0
    jc = (jd - 2451545.0) / 36525.0
    geom_mean_long = np.deg2rad((280.46646 + jc * (36000.76983 + 0.0003032 * jc)) % 360)
    geom_mean_anom = np.deg2rad(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
    eccent = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    sun_eq = (
        np.sin(geom_mean_anom) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + np.sin(2 * geom_mean_anom) * (0.019993 - 0.000101 * jc)
        + np.sin(3 * geom_mean_anom) * 0.000289
    )
    sun_true_long = geom_mean_long + np.deg2rad(sun_eq)
    omega = np.deg2rad(125.04 - 1934.136 * jc)
    sun_app_long = sun_true_long - np.deg2rad(0.00569 + 0.00478 * np.sin(omega))
    mean_obliq = 23 + (26 + ((21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813)))) / 60) / 60
    obliq = np.deg2rad(mean_obliq + 0.00256 * np.cos(omega))
    decl = np.arcsin(np.sin(obliq) * np.sin(sun_app_long))
    var_y = np.tan(obliq / 2) ** 2
    eqtime = 4 * np.rad2deg(
        var_y * np.sin(2 * geom_mean_long)
        - 2 * eccent * np.sin(geom_mean_anom)
        + 4 * eccent * var_y * np.sin(geom_mean_anom) * np.cos(2 * geom_mean_long)
        - 0.5 * var_y ** 2 * np.sin(4 * geom_mean_long)
        - 1.25 * eccent ** 2 * np.sin(2 * geom_mean_anom)
    )
    solar_time = (hour * 60 + eqtime + 4 * lon) % 1440
    ha = np.where(solar_time / 4 < 0, solar_time / 4 + 180, solar_time / 4 - 180)
    ha_r = np.deg2rad(ha)
    zenith = np.arccos(
        np.clip(np.sin(lat_r) * np.sin(decl) + np.cos(lat_r) * np.cos(decl) * np.cos(ha_r), -1, 1)
    )
    az_num = np.sin(ha_r)
    az_den = np.cos(ha_r) * np.sin(lat_r) - np.tan(decl) * np.cos(lat_r)
    azimuth = np.deg2rad(180) + np.arctan2(az_num, az_den)
    etr = 1367.0 * (1 + 0.033 * np.cos(2 * np.pi * ts.dayofyear.values / 365.0))
    return np.rad2deg(zenith), np.rad2deg(azimuth) % 360, etr, np.rad2deg(decl)


def erbs_split(ghi: np.ndarray, zenith: np.ndarray, etr: np.ndarray):
    """Erbs diffuse fraction when DNI/DHI are missing."""
    zen_r = np.deg2rad(np.clip(zenith, 0, 87))
    am = 1.0 / np.maximum(np.cos(zen_r), 0.035)
    i0h = etr * np.cos(zen_r)
    kt = np.clip(np.where(i0h > 10, ghi / i0h, 0), 0, 1.2)
    df = np.where(
        kt <= 0.22,
        1 - 0.09 * kt,
        np.where(
            kt <= 0.80,
            0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4,
            0.165,
        ),
    )
    dhi = ghi * df
    dni = np.where(np.cos(zen_r) > 0.05, (ghi - dhi) / np.cos(zen_r), 0)
    dni = np.clip(dni, 0, 1200)
    return dni, dhi


def kasten_ghi(zenith: np.ndarray, etr: np.ndarray, cloud_pct: np.ndarray) -> np.ndarray:
    """Kasten-Czeplak GHI from cloud cover (used for live NWP without GHI)."""
    zen_r = np.deg2rad(np.clip(zenith, 0, 90))
    clear = etr * np.cos(zen_r) * 0.78  # simple clear-sky
    clear = np.where(zenith < 87, np.maximum(clear, 0), 0)
    c = np.clip(cloud_pct / 100.0, 0, 1)
    return clear * (1 - 0.75 * c**3.4)


def poa_isotropic(ghi, dni, dhi, zenith, azimuth, tilt, surf_az, albedo=0.2):
    zen_r = np.deg2rad(np.clip(zenith, 0, 90))
    az_r = np.deg2rad(azimuth)
    tilt_r = np.deg2rad(tilt)
    sa_r = np.deg2rad(surf_az)
    aoi = np.arccos(
        np.clip(
            np.cos(zen_r) * np.cos(tilt_r)
            + np.sin(zen_r) * np.sin(tilt_r) * np.cos(az_r - sa_r),
            -1,
            1,
        )
    )
    beam = dni * np.maximum(np.cos(aoi), 0)
    sky = dhi * (1 + np.cos(tilt_r)) / 2
    gnd = ghi * albedo * (1 - np.cos(tilt_r)) / 2
    poa = np.where(zenith < 87, beam + sky + gnd, 0)
    return np.clip(poa, 0, 1400)


def pv_ac_mw(poa, temp_c, capacity_mw, dc_ac_ratio, gamma=-0.0038):
    t_cell = temp_c + poa / 800.0 * 28.0  # NOCT-ish
    dc = capacity_mw * dc_ac_ratio * (poa / 1000.0) * (1 + gamma * (t_cell - 25.0))
    dc = np.maximum(dc, 0)
    ac = np.minimum(dc * 0.97, capacity_mw)  # inverter clip + loss
    ac = np.where(poa < 5, 0, ac)
    return ac, t_cell


def wind_cf(v: np.ndarray) -> np.ndarray:
    """Generic IEC Class II power curve as capacity factor."""
    cut_in, rated, cut_out = 3.0, 12.5, 25.0
    cf = np.zeros_like(v, dtype=float)
    mid = (v >= cut_in) & (v < rated)
    cf[mid] = ((v[mid] - cut_in) / (rated - cut_in)) ** 3
    cf[(v >= rated) & (v < cut_out)] = 1.0
    return np.clip(cf, 0, 1)


def wind_ac_mw(v_hub, temp_c, pressure_hpa, capacity_mw):
    tk = temp_c + 273.15
    rho = (pressure_hpa * 100.0) / (287.05 * np.maximum(tk, 240))
    dens = np.clip(rho / 1.225, 0.7, 1.3)
    return capacity_mw * wind_cf(v_hub) * dens


def attach_physics(weather: pd.DataFrame, site: dict) -> pd.DataFrame:
    times = pd.DatetimeIndex(weather["timestamp_utc"])
    if times.tz is None:
        times = times.tz_localize("UTC")
    zenith, azimuth, etr, decl = solar_geometry(site["lat"], site["lon"], times)
    ghi = weather["ghi_wm2"].to_numpy(dtype=float) if "ghi_wm2" in weather else np.full(len(weather), np.nan)
    dni = weather["dni_wm2"].to_numpy(dtype=float) if "dni_wm2" in weather else np.full(len(weather), np.nan)
    dhi = weather["dhi_wm2"].to_numpy(dtype=float) if "dhi_wm2" in weather else np.full(len(weather), np.nan)
    cloud = weather["cloud_pct"].to_numpy(dtype=float)
    # Live NWP has no GHI — synthesise from cloud + geometry.
    need = ~np.isfinite(ghi)
    if need.any():
        ghi = np.where(need, kasten_ghi(zenith, etr, np.nan_to_num(cloud, nan=50)), ghi)
    need_split = ~np.isfinite(dni) | ~np.isfinite(dhi)
    if need_split.any():
        dni_e, dhi_e = erbs_split(np.nan_to_num(ghi, nan=0), zenith, etr)
        dni = np.where(need_split, dni_e, dni)
        dhi = np.where(need_split, dhi_e, dhi)

    temp = weather["temp_c"].to_numpy(dtype=float)
    pres = weather["pressure_hpa"].to_numpy(dtype=float)
    pres = np.where(np.isfinite(pres), pres, 1013.25)

    out = weather.copy()
    out["ghi_wm2"] = ghi
    out["dni_wm2"] = dni
    out["dhi_wm2"] = dhi
    out["zenith_deg"] = zenith
    out["azimuth_deg"] = azimuth
    out["is_day"] = (zenith < 87).astype(int)
    out["hour"] = times.hour
    out["dow"] = times.dayofweek
    out["month"] = times.month
    out["doy"] = times.dayofyear

    if site["tech"] == "solar":
        poa = poa_isotropic(
            ghi, dni, dhi, zenith, azimuth, site["tilt_deg"] or 25, site["azimuth_deg"] or 180
        )
        ac, t_cell = pv_ac_mw(poa, temp, site["capacity_mw"], site["dc_ac_ratio"] or 1.25)
        out["gti_wm2"] = poa
        out["cell_temp_c"] = t_cell
        out["y_physics_mw"] = ac
    else:
        v = weather["wind_ms_hub"].to_numpy(dtype=float)
        ac = wind_ac_mw(v, temp, pres, site["capacity_mw"])
        out["gti_wm2"] = np.nan
        out["cell_temp_c"] = np.nan
        out["y_physics_mw"] = ac
        out["v_hub_ms"] = v

    out["capacity_mw"] = site["capacity_mw"]
    out["capacity_factor"] = out["y_physics_mw"] / site["capacity_mw"]
    out["tech"] = site["tech"]
    out["ba_code"] = site["ba_code"]
    return out


def nwp_corrupt(df: pd.DataFrame, horizon_h: int, rng: np.random.Generator) -> pd.DataFrame:
    """Simulate NWP error that grows with lead time (no look-ahead in the *error* magnitude)."""
    scale = math.sqrt(horizon_h / 24.0)
    out = df.copy()
    ghi_rel = 0.16 * scale
    wind_abs = 1.6 * scale
    temp_abs = 1.4 * scale
    cloud_abs = 12 * scale
    out["ghi_wm2"] = np.clip(out["ghi_wm2"] * rng.lognormal(0, ghi_rel, len(out)), 0, 1300)
    out["dni_wm2"] = np.clip(out["dni_wm2"] * rng.lognormal(0, ghi_rel, len(out)), 0, 1200)
    out["dhi_wm2"] = np.clip(out["dhi_wm2"] * rng.lognormal(0, ghi_rel, len(out)), 0, 800)
    out["wind_ms_80"] = np.clip(out["wind_ms_80"] + rng.normal(0, wind_abs, len(out)), 0, 40)
    out["wind_ms_hub"] = np.clip(out["wind_ms_hub"] + rng.normal(0, wind_abs, len(out)), 0, 40)
    out["temp_c"] = out["temp_c"] + rng.normal(0, temp_abs, len(out))
    out["cloud_pct"] = np.clip(out["cloud_pct"] + rng.normal(0, cloud_abs, len(out)), 0, 100)
    return out


# ---------------------------------------------------------------------------
# Demand
# ---------------------------------------------------------------------------

HOURLY_SHAPE = np.array(
    [
        0.72, 0.68, 0.66, 0.65, 0.66, 0.70, 0.80, 0.90, 0.96, 0.98, 0.99, 1.00,
        1.01, 1.03, 1.06, 1.08, 1.10, 1.09, 1.05, 1.00, 0.94, 0.88, 0.82, 0.76,
    ]
)
WEEKDAY_SCALE = np.array([1.02, 1.03, 1.03, 1.02, 1.00, 0.90, 0.86])  # Mon..Sun


def ba_demand(ba: str, times: pd.DatetimeIndex, temp_c: np.ndarray, rng: np.random.Generator) -> pd.DataFrame:
    stats = BA_LOAD[ba]
    hour = times.hour.values
    dow = times.dayofweek.values
    doy = times.dayofyear.values
    seasonal = 1.0 + 0.12 * np.sin(2 * np.pi * (doy - 200) / 365.0)  # summer peak
    cdd = np.maximum(temp_c - 18.0, 0)
    hdd = np.maximum(15.0 - temp_c, 0)
    weather = 1.0 + stats["k_cdd"] * cdd + stats["k_hdd"] * hdd
    shape = HOURLY_SHAPE[hour] * WEEKDAY_SCALE[dow]
    noise = rng.normal(1.0, 0.02, len(times))
    demand = stats["mean"] * seasonal * shape * weather * noise
    demand = np.clip(demand, stats["min"] * 0.85, stats["max"] * 1.05)
    # Day-ahead forecast: yesterday's same-hour + weather, with error.
    da_err = rng.normal(0, 0.035, len(times))
    da = demand * (1 + da_err)
    return pd.DataFrame(
        {
            "ba_code": ba,
            "timestamp_utc": times,
            "demand_mw": demand,
            "demand_forecast_mw": da,
            "temp_ba_c": temp_c,
            "source": "temp_calibrated_typical",
        }
    )


# ---------------------------------------------------------------------------
# Actions / flags
# ---------------------------------------------------------------------------

def flag_rows(panel: pd.DataFrame) -> pd.DataFrame:
    """Plant-level and BA-level flags."""
    df = panel.sort_values(["site_id", "timestamp_utc"]).copy()
    df["y_l24"] = df.groupby("site_id")["y_physics_mw"].shift(24)
    # Plant vs day-ahead physics (persistence of CF * capacity as naive schedule)
    df["schedule_mw"] = df["y_l24"].fillna(df["y_physics_mw"])
    df["plant_delta_mw"] = df["y_physics_mw"] - df["schedule_mw"]
    cap = df["capacity_mw"]
    df["flag_plant_over"] = (df["plant_delta_mw"] > 0.12 * cap).astype(int)
    df["flag_plant_under"] = (df["plant_delta_mw"] < -0.12 * cap).astype(int)
    df["ramp_mw"] = df.groupby("site_id")["y_physics_mw"].diff()
    df["flag_ramp"] = (df["ramp_mw"].abs() > 0.18 * cap).astype(int)
    return df


def recommend(delta_mw: float, storage_headroom: float, storage_soc: float) -> str:
    if delta_mw > 40 and storage_headroom > 10:
        return "charge_storage"
    if delta_mw > 40:
        return "curtail"
    if delta_mw < -40 and storage_soc > 10:
        return "discharge_storage"
    if delta_mw < -40:
        return "activate_backup"
    return "do_nothing"


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_csv_gz(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")
    log(f"  wrote {path.name}  rows={len(df):,}  bytes={path.stat().st_size:,}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)
    log(f"  wrote {path.name}  rows={len(df):,}")


def slim_records(df: pd.DataFrame, cols: list[str], n: int | None = None) -> list:
    x = df[cols] if cols else df
    if n:
        x = x.head(n)
    x = x.replace({np.nan: None})
    rec = x.to_dict(orient="records")
    # Round floats for a smaller UI payload.
    out = []
    for row in rec:
        clean = {}
        for k, v in row.items():
            if isinstance(v, float):
                clean[k] = None if not math.isfinite(v) else round(v, 3)
            elif isinstance(v, pd.Timestamp):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        out.append(clean)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()
    sites_df = pd.DataFrame(SITES)
    write_csv(sites_df, OUT / "sites.csv")
    (OUT / "sites.json").write_text(sites_df.to_json(orient="records", indent=2))

    log("Fetching NASA POWER historical weather (8 sites × 2 years)…")
    weather_parts = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(fetch_site_weather, s): s["site_id"] for s in SITES}
        for fut in as_completed(futs):
            sid = futs[fut]
            try:
                weather_parts.append(fut.result())
                log(f"  ok {sid}")
            except Exception as e:  # noqa: BLE001
                log(f"  FAIL {sid}: {e}")
    if not weather_parts:
        raise SystemExit("No weather downloaded")
    weather = pd.concat(weather_parts, ignore_index=True)
    weather["timestamp_utc"] = pd.to_datetime(weather["timestamp_utc"], utc=True)
    write_csv_gz(weather, OUT / "weather_hourly.csv.gz")
    weather.to_pickle(RAW / "weather_hourly.pkl")

    log("Running physics (pvlib-lite + IEC wind curve)…")
    gen_parts = []
    for s in SITES:
        w = weather[weather["site_id"] == s["site_id"]].copy()
        if w.empty:
            continue
        gen_parts.append(attach_physics(w, s))
    gen = pd.concat(gen_parts, ignore_index=True)
    write_csv_gz(
        gen[
            [
                "site_id",
                "timestamp_utc",
                "tech",
                "ba_code",
                "y_physics_mw",
                "capacity_mw",
                "capacity_factor",
                "gti_wm2",
                "cell_temp_c",
                "zenith_deg",
                "is_day",
                "ghi_wm2",
                "wind_ms_hub",
                "temp_c",
            ]
        ],
        OUT / "generation_hourly.csv.gz",
    )

    log("Building BA demand from regional temperature…")
    ba_frames = []
    rng_ba = np.random.default_rng(7)
    for ba in ("CISO", "ERCO"):
        sub = gen[gen["ba_code"] == ba]
        tmp = sub.groupby("timestamp_utc")["temp_c"].mean()
        times = pd.DatetimeIndex(tmp.index)
        ba_frames.append(ba_demand(ba, times, tmp.to_numpy(), rng_ba))
    ba = pd.concat(ba_frames, ignore_index=True)
    # Attach fleet renewable (the 8 plants) and implied other generation.
    fleet = gen.groupby(["ba_code", "timestamp_utc"], as_index=False)["y_physics_mw"].sum()
    fleet = fleet.rename(columns={"y_physics_mw": "fleet_renewable_mw"})
    ba = ba.merge(fleet, on=["ba_code", "timestamp_utc"], how="left")
    ba["fleet_renewable_mw"] = ba["fleet_renewable_mw"].fillna(0)
    # Scale a "full BA renewable" using typical penetration so net-load flags are meaningful.
    # CAISO ~ 30% of demand from wind+solar on average; ERCOT ~ 35%.
    pen = ba["ba_code"].map({"CISO": 0.30, "ERCO": 0.34})
    # Use fleet CF as the renewable shape, scaled to penetration * demand.
    fleet_cap = sites_df.groupby("ba_code")["capacity_mw"].sum()
    ba["fleet_cap_mw"] = ba["ba_code"].map(fleet_cap)
    ba["ba_renewable_mw"] = (ba["fleet_renewable_mw"] / ba["fleet_cap_mw"]) * pen * ba["demand_mw"]
    ba["net_load_mw"] = ba["demand_mw"] - ba["ba_renewable_mw"]
    ba["delta_mw"] = ba["ba_renewable_mw"] - ba["demand_mw"] * 0.0  # kept for schema
    # Over: net load very low (renewable covering almost all demand)
    q10 = ba.groupby("ba_code")["net_load_mw"].transform(lambda s: s.quantile(0.12))
    q90 = ba.groupby("ba_code")["net_load_mw"].transform(lambda s: s.quantile(0.88))
    ba["flag_over"] = (ba["net_load_mw"] <= q10).astype(int)
    ba["flag_under"] = (ba["net_load_mw"] >= q90).astype(int)
    ba["action"] = [
        recommend(
            (row.net_load_mw - row.demand_mw * 0.55) * -1,  # surplus if net load low
            80,
            40,
        )
        if False
        else (
            "charge_storage"
            if row.flag_over
            else "activate_backup"
            if row.flag_under
            else "do_nothing"
        )
        for row in ba.itertuples()
    ]
    write_csv_gz(ba, OUT / "ba_hourly.csv.gz")

    log("Joining panel…")
    panel = gen.merge(ba, on=["ba_code", "timestamp_utc"], how="left")
    panel = flag_rows(panel)
    # Keep a lean panel for download
    panel_cols = [
        "site_id",
        "timestamp_utc",
        "tech",
        "ba_code",
        "ghi_wm2",
        "dni_wm2",
        "dhi_wm2",
        "temp_c",
        "rh_pct",
        "cloud_pct",
        "wind_ms_10",
        "wind_ms_80",
        "wind_ms_hub",
        "wind_dir_80",
        "pressure_hpa",
        "zenith_deg",
        "is_day",
        "gti_wm2",
        "y_physics_mw",
        "capacity_mw",
        "capacity_factor",
        "demand_mw",
        "demand_forecast_mw",
        "ba_renewable_mw",
        "net_load_mw",
        "flag_over",
        "flag_under",
        "flag_plant_over",
        "flag_plant_under",
        "flag_ramp",
        "hour",
        "dow",
        "month",
        "doy",
    ]
    panel = panel[panel_cols]
    write_csv_gz(panel, OUT / "panel_hourly.csv.gz")

    log("Building train matrices for h = 24, 48, 72…")
    site_map = {s["site_id"]: s for s in SITES}
    for h in (24, 48, 72):
        rows = []
        for sid, g in panel.groupby("site_id"):
            g = g.sort_values("timestamp_utc").reset_index(drop=True)
            rng = np.random.default_rng(abs(hash(sid)) % (2**32) + h)
            # Issue every 3 hours to keep files tractable.
            issue_idx = np.arange(48, len(g) - h, 3)
            weather_cols = [
                "ghi_wm2",
                "dni_wm2",
                "dhi_wm2",
                "temp_c",
                "rh_pct",
                "cloud_pct",
                "wind_ms_80",
                "wind_ms_hub",
                "pressure_hpa",
            ]
            actual_future = g.iloc[issue_idx + h].reset_index(drop=True)
            issue = g.iloc[issue_idx].reset_index(drop=True)
            nwp = nwp_corrupt(actual_future[weather_cols].copy(), h, rng)
            s = site_map[sid]
            rec = pd.DataFrame(
                {
                    "site_id": sid,
                    "tech": s["tech"],
                    "ba_code": s["ba_code"],
                    "capacity_mw": s["capacity_mw"],
                    "tilt_deg": s["tilt_deg"],
                    "azimuth_deg": s["azimuth_deg"],
                    "hub_height_m": s["hub_height_m"],
                    "issue_time_utc": issue["timestamp_utc"].values,
                    "valid_time_utc": actual_future["timestamp_utc"].values,
                    "horizon_h": h,
                    "y_mw": actual_future["y_physics_mw"].values,
                    "y_physics_nwp_mw": None,
                    "y_lag0_mw": issue["y_physics_mw"].values,
                    "y_lag24_mw": g["y_physics_mw"].shift(24).iloc[issue_idx].values,
                    "hour": actual_future["hour"].values,
                    "dow": actual_future["dow"].values,
                    "month": actual_future["month"].values,
                    "doy": actual_future["doy"].values,
                    "is_day": actual_future["is_day"].values,
                    "zenith_deg": actual_future["zenith_deg"].values,
                    "demand_mw": actual_future["demand_mw"].values,
                }
            )
            for c in weather_cols:
                rec[f"nwp_{c}"] = nwp[c].values
                rec[f"actual_{c}"] = actual_future[c].values
            # Physics on corrupted NWP weather (the baseline the ML should beat).
            nwp_w = actual_future.copy()
            for c in weather_cols:
                nwp_w[c] = nwp[c].values
            nwp_w["wind_ms_10"] = nwp_w["wind_ms_80"] * (10 / 80) ** 0.143
            nwp_phys = attach_physics(nwp_w, s)
            rec["y_physics_nwp_mw"] = nwp_phys["y_physics_mw"].values
            rec["residual_mw"] = rec["y_mw"] - rec["y_physics_nwp_mw"]
            rows.append(rec)
        train = pd.concat(rows, ignore_index=True)
        write_csv_gz(train, OUT / f"model_train_h{h}.csv.gz")
        if h == 24:
            train_h24 = train

    log("Fetching live 72h MET Norway forecast…")
    fc_parts = []
    for s in SITES:
        try:
            raw = fetch_metno_forecast(s)
            fc_parts.append(attach_physics(raw, s))
            log(f"  forecast ok {s['site_id']}")
            time.sleep(0.3)
        except Exception as e:  # noqa: BLE001
            log(f"  forecast FAIL {s['site_id']}: {e}")
    if fc_parts:
        fc = pd.concat(fc_parts, ignore_index=True)
        # Attach BA demand forecast using forecast temps.
        fc_ba = []
        rng_f = np.random.default_rng(11)
        for ba_code in ("CISO", "ERCO"):
            sub = fc[fc["ba_code"] == ba_code]
            tmp = sub.groupby("timestamp_utc")["temp_c"].mean()
            fc_ba.append(ba_demand(ba_code, pd.DatetimeIndex(tmp.index), tmp.to_numpy(), rng_f))
        fc = fc.merge(pd.concat(fc_ba, ignore_index=True), on=["ba_code", "timestamp_utc"], how="left")
        # Quantile bands: physics ± growing-with-horizon NWP uncertainty.
        now = pd.Timestamp.now(tz="UTC").floor("h")
        fc["horizon_h"] = ((fc["timestamp_utc"] - now) / pd.Timedelta(hours=1)).round().astype(int)
        band = (0.08 + 0.004 * fc["horizon_h"].clip(lower=0)) * fc["capacity_mw"]
        fc["q10_mw"] = (fc["y_physics_mw"] - 1.28 * band).clip(lower=0)
        fc["q50_mw"] = fc["y_physics_mw"]
        fc["q90_mw"] = fc["y_physics_mw"] + 1.28 * band
        fc["q90_mw"] = np.minimum(fc["q90_mw"], fc["capacity_mw"])
        fc_out = fc[
            [
                "site_id",
                "timestamp_utc",
                "tech",
                "ba_code",
                "horizon_h",
                "ghi_wm2",
                "temp_c",
                "cloud_pct",
                "wind_ms_80",
                "y_physics_mw",
                "q10_mw",
                "q50_mw",
                "q90_mw",
                "capacity_mw",
                "capacity_factor",
                "demand_forecast_mw",
                "demand_mw",
            ]
        ]
        write_csv(fc_out, OUT / "forecast_72h.csv")
        fc_out.to_json(UI / "forecast.json", orient="records", date_format="iso")
    else:
        fc_out = pd.DataFrame()

    log("Writing UI summaries…")
    panel["date"] = panel["timestamp_utc"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%d")
    daily = (
        panel.groupby(["site_id", "tech", "ba_code", "date"], as_index=False)
        .agg(
            y_mwh=("y_physics_mw", "sum"),
            cf_mean=("capacity_factor", "mean"),
            ghi_mean=("ghi_wm2", "mean"),
            wind_mean=("wind_ms_80", "mean"),
            temp_mean=("temp_c", "mean"),
            flag_over=("flag_over", "max"),
            flag_under=("flag_under", "max"),
            demand_mean=("demand_mw", "mean"),
        )
    )
    daily.to_json(UI / "daily.json", orient="records")

    last_ts = panel["timestamp_utc"].max()
    recent = panel[panel["timestamp_utc"] >= last_ts - pd.Timedelta(days=14)].copy()
    recent_cols = [
        "site_id",
        "timestamp_utc",
        "tech",
        "y_physics_mw",
        "ghi_wm2",
        "wind_ms_80",
        "temp_c",
        "capacity_factor",
        "demand_mw",
        "net_load_mw",
        "flag_over",
        "flag_under",
        "flag_ramp",
    ]
    (UI / "recent_hourly.json").write_text(
        json.dumps(slim_records(recent, recent_cols), default=str)
    )

    ba_daily = (
        ba.assign(date=ba["timestamp_utc"].dt.strftime("%Y-%m-%d"))
        .groupby(["ba_code", "date"], as_index=False)
        .agg(
            demand_mean=("demand_mw", "mean"),
            demand_max=("demand_mw", "max"),
            renewable_mean=("ba_renewable_mw", "mean"),
            net_load_mean=("net_load_mw", "mean"),
            over_hours=("flag_over", "sum"),
            under_hours=("flag_under", "sum"),
        )
    )
    ba_daily.to_json(UI / "ba_daily.json", orient="records")

    sample = train_h24.sample(n=min(2500, len(train_h24)), random_state=0)
    sample.to_json(UI / "model_sample.json", orient="records", date_format="iso")

    overview = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sites": len(SITES),
        "weather_rows": int(len(weather)),
        "generation_rows": int(len(gen)),
        "ba_rows": int(len(ba)),
        "panel_rows": int(len(panel)),
        "train_h24_rows": int(len(train_h24)),
        "forecast_rows": int(len(fc_out)),
        "start": str(panel["timestamp_utc"].min()),
        "end": str(panel["timestamp_utc"].max()),
        "capacity_mw_total": float(sites_df["capacity_mw"].sum()),
        "sources": {
            "sites": "WRI Global Power Plant Database / EIA-860 identities",
            "weather_historical": "NASA POWER hourly (MERRA-2), community=RE",
            "weather_forecast": "MET Norway Locationforecast 2.0 (cloud→GHI via Kasten-Czeplak)",
            "generation": "Physics: isotropic POA + PV inverter clip; IEC Class II wind curve + density",
            "demand": "Temperature-calibrated typical load (CAISO/ERCOT published mean/peak)",
            "nwp_features": "MERRA-2 actuals + lead-time-scaled Gaussian/lognormal error (no look-ahead in magnitude)",
        },
        "notes": [
            "Open-Meteo returned HTTP 429 (daily cap) from this network — NASA POWER is the drop-in historical source with the same columns.",
            "EIA Grid Monitor returned 503 — BA demand is a temperature-driven model calibrated to published CAISO/ERCOT ranges, not Form 930.",
            "y_physics_mw is the training target for the live demo (no public plant SCADA at these sites).",
            "Over/under at BA level = net load in the lower/upper 12% of that BA's distribution.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(overview, indent=2))
    (UI / "overview.json").write_text(json.dumps(overview, indent=2))

    schema = {
        "sites": {
            "grain": "1 row = 1 plant",
            "pk": ["site_id"],
            "columns": list(sites_df.columns),
        },
        "weather_hourly": {
            "grain": "1 row = site × hour",
            "pk": ["site_id", "timestamp_utc"],
            "source": "NASA POWER",
        },
        "generation_hourly": {
            "grain": "1 row = site × hour",
            "pk": ["site_id", "timestamp_utc"],
            "target": "y_physics_mw",
        },
        "ba_hourly": {
            "grain": "1 row = BA × hour",
            "pk": ["ba_code", "timestamp_utc"],
        },
        "panel_hourly": {
            "grain": "1 row = site × hour (S ⋈ W ⋈ P ⋈ D)",
            "pk": ["site_id", "timestamp_utc"],
        },
        "model_train_h24": {
            "grain": "1 row = site × issue_time × horizon",
            "input": "nwp_* weather at valid time, lags at issue time, site params, calendar",
            "output": "y_mw (physics on actual weather at t+h)",
            "baseline": "y_physics_nwp_mw",
        },
        "forecast_72h": {
            "grain": "1 row = site × future hour",
            "output": ["q10_mw", "q50_mw", "q90_mw"],
        },
    }
    (OUT / "schema.json").write_text(json.dumps(schema, indent=2))

    log(f"DONE in {time.time()-t0:.1f}s")
    log(json.dumps(overview, indent=2))


if __name__ == "__main__":
    main()
