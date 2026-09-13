#!/usr/bin/env python3
"""Train solar/wind residual quantile GBMs and score the live 72h forecast.

Hybrid: Ŷ_τ = clip( physics(W, S) + r_τ(φ(x)), 0, capacity )
τ ∈ {0.1, 0.5, 0.9} via sklearn HistGradientBoostingRegressor on the residual.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_pinball_loss

from build_sirocco_dataset import SITES, erbs_split, solar_geometry

ROOT = Path("/workspace")
OUT = ROOT / "public" / "data"
UI = OUT / "ui"
UI.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "horizon_h",
    "hour",
    "dow",
    "month",
    "doy",
    "is_day",
    "zenith_deg",
    "capacity_mw",
    "tilt_deg",
    "azimuth_deg",
    "hub_height_m",
    "y_lag0_mw",
    "y_lag24_mw",
    "nwp_ghi_wm2",
    "nwp_dni_wm2",
    "nwp_dhi_wm2",
    "nwp_temp_c",
    "nwp_rh_pct",
    "nwp_cloud_pct",
    "nwp_wind_ms_80",
    "nwp_wind_ms_hub",
    "nwp_pressure_hpa",
    "y_physics_nwp_mw",
]
SPLIT = pd.Timestamp("2026-03-01")
TAUS = (0.1, 0.5, 0.9)


def log(msg: str) -> None:
    print(msg, flush=True)


def load_train() -> pd.DataFrame:
    parts = [pd.read_csv(OUT / f"model_train_h{h}.csv.gz") for h in (24, 48, 72)]
    df = pd.concat(parts, ignore_index=True)
    df["issue_time_utc"] = pd.to_datetime(df["issue_time_utc"])
    df["valid_time_utc"] = pd.to_datetime(df["valid_time_utc"])
    for c in ("tilt_deg", "azimuth_deg", "hub_height_m"):
        df[c] = df[c].fillna(0.0)
    df[FEATURES] = df[FEATURES].astype(float)
    df["residual_mw"] = df["y_mw"] - df["y_physics_nwp_mw"]
    return df


def fit_quantile(X: np.ndarray, y: np.ndarray, tau: float) -> HistGradientBoostingRegressor:
    m = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=tau,
        max_depth=5,
        max_iter=180,
        learning_rate=0.06,
        min_samples_leaf=60,
        l2_regularization=0.4,
        max_bins=96,
        early_stopping=False,
        random_state=42,
    )
    m.fit(X, y)
    return m


def clip_quantiles(q10, q50, q90, cap, night_mask):
    q50 = np.clip(q50, 0, cap)
    q10 = np.minimum(np.clip(q10, 0, cap), q50)
    q90 = np.maximum(np.clip(q90, 0, cap), q50)
    if night_mask is not None:
        q10 = np.where(night_mask, 0.0, q10)
        q50 = np.where(night_mask, 0.0, q50)
        q90 = np.where(night_mask, 0.0, q90)
    return q10, q50, q90


def pressure_from_alt(alt_m: float) -> float:
    return 1013.25 * math.exp(-float(alt_m) / 8500.0)


def predict_hybrid(models_tech: dict, d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = d[FEATURES].to_numpy()
    phys = d["y_physics_nwp_mw"].to_numpy()
    cap = d["capacity_mw"].to_numpy()
    night = ((d["tech"] == "solar") & (d["is_day"] < 0.5)).to_numpy()
    q10 = phys + models_tech[0.1].predict(X)
    q50 = phys + models_tech[0.5].predict(X)
    q90 = phys + models_tech[0.9].predict(X)
    return clip_quantiles(q10, q50, q90, cap, night)


def score_split(models: dict, d: pd.DataFrame, tech: str) -> dict:
    y = d["y_mw"].to_numpy()
    base = np.clip(d["y_physics_nwp_mw"].to_numpy(), 0, d["capacity_mw"].to_numpy())
    q10, q50, q90 = predict_hybrid(models[tech], d)
    mae = float(mean_absolute_error(y, q50))
    mae_base = float(mean_absolute_error(y, base))
    cap_mean = float(np.mean(d["capacity_mw"])) or 1.0
    return {
        "n": int(len(d)),
        "mae_mw": round(mae, 3),
        "mae_baseline_mw": round(mae_base, 3),
        "mae_skill": round(1.0 - mae / max(mae_base, 1e-6), 4),
        "mae_pct_capacity": round(100.0 * mae / cap_mean, 2),
        "pinball": {
            "p10": round(float(mean_pinball_loss(y, q10, alpha=0.1)), 3),
            "p50": round(float(mean_pinball_loss(y, q50, alpha=0.5)), 3),
            "p90": round(float(mean_pinball_loss(y, q90, alpha=0.9)), 3),
        },
        "coverage_80": round(float(np.mean((y >= q10) & (y <= q90))), 4),
        "n_iter": {str(t): int(models[tech][t].n_iter_) for t in TAUS},
    }


def engineer_forecast(fc: pd.DataFrame, sites: list[dict]) -> pd.DataFrame:
    site_map = {s["site_id"]: s for s in sites}
    rows = []
    fc = fc.copy()
    fc["timestamp_utc"] = pd.to_datetime(fc["timestamp_utc"], utc=True)
    for sid, g in fc.groupby("site_id", sort=False):
        g = g.sort_values("timestamp_utc").reset_index(drop=True)
        s = site_map[sid]
        times = pd.DatetimeIndex(g["timestamp_utc"])
        zenith, az, etr, _ = solar_geometry(s["lat"], s["lon"], times)
        ghi = g["ghi_wm2"].to_numpy(dtype=float)
        dni, dhi = erbs_split(np.nan_to_num(ghi, nan=0.0), zenith, etr)
        temp = g["temp_c"].to_numpy(dtype=float)
        cloud = g["cloud_pct"].to_numpy(dtype=float)
        wind80 = g["wind_ms_80"].to_numpy(dtype=float)
        hub = float(s["hub_height_m"] or 80.0)
        wind_hub = wind80 * (hub / 80.0) ** 0.143
        pres = pressure_from_alt(s["altitude_m"])
        y_phys = g["y_physics_mw"].to_numpy(dtype=float)
        lag0 = float(y_phys[0])
        rec = pd.DataFrame(
            {
                "site_id": sid,
                "tech": s["tech"],
                "ba_code": s["ba_code"],
                "timestamp_utc": times,
                "horizon_h": g["horizon_h"].to_numpy(dtype=float),
                "hour": times.hour.astype(float),
                "dow": times.dayofweek.astype(float),
                "month": times.month.astype(float),
                "doy": times.dayofyear.astype(float),
                "is_day": (zenith < 87).astype(float),
                "zenith_deg": zenith,
                "sun_azimuth_deg": az,
                "capacity_mw": float(s["capacity_mw"]),
                "tilt_deg": float(s["tilt_deg"] or 0.0),
                "azimuth_deg": float(s["azimuth_deg"] or 0.0),
                "hub_height_m": float(s["hub_height_m"] or 0.0),
                "y_lag0_mw": lag0,
                "nwp_ghi_wm2": ghi,
                "nwp_dni_wm2": dni,
                "nwp_dhi_wm2": dhi,
                "nwp_temp_c": temp,
                "nwp_rh_pct": 40.0,
                "nwp_cloud_pct": cloud,
                "nwp_wind_ms_80": wind80,
                "nwp_wind_ms_hub": wind_hub,
                "nwp_pressure_hpa": pres,
                "y_physics_nwp_mw": y_phys,
                "demand_mw": g["demand_mw"].to_numpy(dtype=float),
                "demand_forecast_mw": g["demand_forecast_mw"].to_numpy(dtype=float),
            }
        )
        rec["y_lag24_mw"] = rec["y_physics_nwp_mw"].shift(24).fillna(lag0)
        rows.append(rec)
    return pd.concat(rows, ignore_index=True)


def r(v, n=3):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return 0.0
    return round(float(v), n)


def main() -> None:
    t0 = time.time()
    log("Loading train matrices…")
    df = load_train()
    train = df[df["issue_time_utc"] < SPLIT]
    valid = df[df["issue_time_utc"] >= SPLIT]
    log(f"  train={len(train):,}  valid={len(valid):,}")

    models: dict = {"solar": {}, "wind": {}}
    metrics = {"split": str(SPLIT.date()), "features": FEATURES, "target": "residual_mw", "tech": {}}

    for tech in ("solar", "wind"):
        tr = train[train["tech"] == tech]
        va = valid[valid["tech"] == tech]
        Xtr = tr[FEATURES].to_numpy()
        ytr = tr["residual_mw"].to_numpy()
        log(f"Fitting {tech} residual  n={len(tr):,}  residual std={float(np.std(ytr)):.2f}")
        for tau in TAUS:
            t1 = time.time()
            models[tech][tau] = fit_quantile(Xtr, ytr, tau)
            log(f"  τ={tau}  iter={models[tech][tau].n_iter_}  {time.time()-t1:.1f}s")
        metrics["tech"][tech] = {
            "train": score_split(models, tr, tech),
            "valid": score_split(models, va, tech),
        }
        v = metrics["tech"][tech]["valid"]
        log(f"  valid MAE {v['mae_mw']} vs base {v['mae_baseline_mw']}  skill {v['mae_skill']}  cov {v['coverage_80']}")

    log("Scoring live 72h…")
    fc = pd.read_csv(OUT / "forecast_72h.csv")
    # drop previous residual cols if re-run
    fc = fc.drop(columns=[c for c in fc.columns if c.startswith("res") and c.endswith("_mw")], errors="ignore")
    eng = engineer_forecast(fc, SITES)
    for tech in ("solar", "wind"):
        mask = eng["tech"] == tech
        q10, q50, q90 = predict_hybrid(models[tech], eng.loc[mask])
        eng.loc[mask, "q10_mw"] = q10
        eng.loc[mask, "q50_mw"] = q50
        eng.loc[mask, "q90_mw"] = q90

    eng["res10_mw"] = eng["q10_mw"] - eng["y_physics_nwp_mw"]
    eng["res50_mw"] = eng["q50_mw"] - eng["y_physics_nwp_mw"]
    eng["res90_mw"] = eng["q90_mw"] - eng["y_physics_nwp_mw"]

    fc["timestamp_utc"] = pd.to_datetime(fc["timestamp_utc"], utc=True)
    scored = fc.merge(
        eng[["site_id", "timestamp_utc", "q10_mw", "q50_mw", "q90_mw", "res10_mw", "res50_mw", "res90_mw"]],
        on=["site_id", "timestamp_utc"],
        how="left",
        suffixes=("_old", ""),
    )
    for c in ("q10_mw", "q50_mw", "q90_mw"):
        old = f"{c}_old"
        if old in scored.columns:
            scored[c] = scored[c].fillna(scored[old])
            scored.drop(columns=[old], inplace=True)

    scored["capacity_factor"] = scored["q50_mw"] / scored["capacity_mw"]
    keep = [
        "site_id", "timestamp_utc", "tech", "ba_code", "horizon_h",
        "ghi_wm2", "temp_c", "cloud_pct", "wind_ms_80",
        "y_physics_mw", "q10_mw", "q50_mw", "q90_mw",
        "capacity_mw", "capacity_factor", "demand_forecast_mw", "demand_mw",
        "res10_mw", "res50_mw", "res90_mw",
    ]
    scored[keep].to_csv(OUT / "forecast_72h.csv", index=False)

    hours = (
        eng[eng["site_id"] == SITES[0]["site_id"]]
        .sort_values("timestamp_utc")["timestamp_utc"]
        .dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        .tolist()
    )

    plants = {}
    for sid, g in eng.groupby("site_id", sort=False):
        g = g.sort_values("timestamp_utc")
        plants[sid] = {
            "ghi": [r(v, 1) for v in g["nwp_ghi_wm2"]],
            "dni": [r(v, 1) for v in g["nwp_dni_wm2"]],
            "dhi": [r(v, 1) for v in g["nwp_dhi_wm2"]],
            "temp": [r(v, 2) for v in g["nwp_temp_c"]],
            "cloud": [r(v, 1) for v in g["nwp_cloud_pct"]],
            "wind80": [r(v, 3) for v in g["nwp_wind_ms_80"]],
            "pressure": [r(v, 2) for v in g["nwp_pressure_hpa"]],
            "zenith": [r(v, 2) for v in g["zenith_deg"]],
            "sunAz": [r(v, 2) for v in g["sun_azimuth_deg"]],
            "yPhys": [r(v, 3) for v in g["y_physics_nwp_mw"]],
            "res10": [r(v, 3) for v in g["res10_mw"]],
            "res50": [r(v, 3) for v in g["res50_mw"]],
            "res90": [r(v, 3) for v in g["res90_mw"]],
        }

    ba = {}
    for code in ("CISO", "ERCO"):
        one = eng[eng["ba_code"] == code].drop_duplicates("timestamp_utc").sort_values("timestamp_utc")
        ba[code] = {
            "demand": [r(v, 1) for v in one["demand_mw"]],
            "demandForecast": [r(v, 1) for v in one["demand_forecast_mw"]],
        }

    # JSON-safe sites (None → null)
    sites_out = []
    for s in SITES:
        sites_out.append({k: v for k, v in s.items()})

    live = {
        "issuedAt": hours[0],
        "horizonH": 72,
        "hours": hours,
        "penetration": {"CISO": 0.30, "ERCO": 0.34},
        "metrics": {
            "split": metrics["split"],
            "target": "residual_mw",
            "solar": metrics["tech"]["solar"]["valid"],
            "wind": metrics["tech"]["wind"]["valid"],
        },
        "sites": sites_out,
        "ba": ba,
        "plants": plants,
    }
    (UI / "live.json").write_text(json.dumps(live, separators=(",", ":")))
    (UI / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log(f"  wrote live.json  {(UI/'live.json').stat().st_size:,} bytes")

    slim = scored[["site_id", "timestamp_utc", "tech", "ba_code", "horizon_h",
                   "ghi_wm2", "temp_c", "wind_ms_80", "y_physics_mw",
                   "q10_mw", "q50_mw", "q90_mw", "capacity_mw",
                   "demand_mw", "demand_forecast_mw"]].copy()
    slim["timestamp_utc"] = pd.to_datetime(slim["timestamp_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    (UI / "forecast.json").write_text(
        json.dumps(
            [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}
             for row in slim.to_dict(orient="records")],
            separators=(",", ":"),
        )
    )

    metrics["elapsed_s"] = round(time.time() - t0, 1)
    (UI / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log(f"Done in {metrics['elapsed_s']}s")
    print(json.dumps({k: metrics["tech"][k]["valid"] for k in metrics["tech"]}, indent=2))


if __name__ == "__main__":
    main()
