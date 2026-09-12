import numpy as np
import pandas as pd
import pvlib
from typing import Dict, Any, List, Optional
from app.config import SOLAR_FLEET_CAPACITY_MW, WIND_FLEET_CAPACITY_MW

class FleetSolarSimulator:
    """
    Physics-informed Digital Twin for the 545 MW Solar Fleet (8 stations).
    Computes instantaneous generation impacts when varying:
    - Installed Capacity (MW)
    - Array Tilt Angle (deg)
    - Array Azimuth Angle (deg)
    - Inverter AC Export Limit (MW)
    - Dust / Soiling Loss Factor (%)
    """

    def __init__(self, lat: float = 36.5, lon: float = 101.5):
        self.lat = lat
        self.lon = lon
        self.baseline_capacity_mw = SOLAR_FLEET_CAPACITY_MW
        self.baseline_tilt = 30.0
        self.baseline_azimuth = 180.0
        self.baseline_inverter_mw = SOLAR_FLEET_CAPACITY_MW
        self.baseline_soiling_pct = 3.0

    def simulate(
        self,
        time_series_df: pd.DataFrame,
        sim_capacity_mw: float = 545.0,
        sim_tilt: float = 30.0,
        sim_azimuth: float = 180.0,
        sim_inverter_mw: float = 545.0,
        sim_soiling_pct: float = 3.0
    ) -> Dict[str, Any]:
        df = time_series_df.copy()
        if "time" in df.columns:
            timestamps = pd.to_datetime(df["time"])
        elif "timestamp" in df.columns:
            timestamps = pd.to_datetime(df["timestamp"])
        else:
            timestamps = pd.date_range("2020-07-01 00:00:00", periods=len(df), freq="15min")

        # Baseline generation MW
        if "total_power_mw" in df.columns:
            base_mw = df["total_power_mw"].fillna(0.0).values
        elif "generation_mw" in df.columns:
            base_mw = df["generation_mw"].fillna(0.0).values
        elif "power_mw" in df.columns:
            base_mw = df["power_mw"].fillna(0.0).values
        else:
            base_mw = np.zeros(len(df))

        # Solar position via pvlib
        loc = pvlib.location.Location(self.lat, self.lon)
        solpos = loc.get_solarposition(timestamps)
        zenith = np.array(solpos["zenith"].values)
        azimuth = np.array(solpos["azimuth"].values)

        cos_zen = np.maximum(0.0, np.cos(np.radians(zenith)))
        ghi = np.maximum(0.0, 1050.0 * cos_zen * np.exp(-0.06 / (cos_zen + 1e-3)))
        dni = 920.0 * cos_zen
        dhi = np.maximum(0.0, ghi - dni * cos_zen)

        # Baseline POA
        poa_base_dict = pvlib.irradiance.get_total_irradiance(
            surface_tilt=self.baseline_tilt,
            surface_azimuth=self.baseline_azimuth,
            solar_zenith=zenith,
            solar_azimuth=azimuth,
            dni=dni,
            ghi=ghi,
            dhi=dhi
        )
        poa_base = np.nan_to_num(np.asarray(poa_base_dict["poa_global"]), nan=0.0)

        # Simulated POA
        poa_sim_dict = pvlib.irradiance.get_total_irradiance(
            surface_tilt=sim_tilt,
            surface_azimuth=sim_azimuth,
            solar_zenith=zenith,
            solar_azimuth=azimuth,
            dni=dni,
            ghi=ghi,
            dhi=dhi
        )
        poa_sim = np.nan_to_num(np.asarray(poa_sim_dict["poa_global"]), nan=0.0)

        # Transposition ratio
        eps = 1e-4
        transposition_ratio = np.where(poa_base > eps, poa_sim / (poa_base + eps), 1.0)
        transposition_ratio = np.clip(transposition_ratio, 0.0, 2.5)

        # Capacity scaling
        capacity_ratio = sim_capacity_mw / self.baseline_capacity_mw

        # Soiling factor adjustment
        soiling_factor = (100.0 - sim_soiling_pct) / (100.0 - self.baseline_soiling_pct)

        # Raw simulated MW
        sim_mw_raw = base_mw * transposition_ratio * capacity_ratio * soiling_factor

        # Inverter clipping limit
        sim_mw_clipped = np.minimum(sim_mw_raw, sim_inverter_mw)
        sim_mw_clipped = np.maximum(0.0, sim_mw_clipped)

        # Summary KPIs (MWh for the evaluated duration, 15min intervals)
        total_baseline_mwh = float(np.sum(base_mw) * 0.25)
        total_sim_mwh = float(np.sum(sim_mw_clipped) * 0.25)
        delta_mwh = total_sim_mwh - total_baseline_mwh
        pct_change = float((delta_mwh / (total_baseline_mwh + 1e-6)) * 100.0)

        # Build visual slice (up to 96 points for clean 24h UI rendering)
        interval_count = min(96, len(df))
        step = max(1, len(df) // interval_count)
        indices = list(range(0, len(df), step))[:96]

        intervals = []
        for i in indices:
            t_str = str(timestamps.iloc[i]) if hasattr(timestamps, "iloc") else str(timestamps[i])
            b_val = round(float(base_mw[i]), 2)
            s_val = round(float(sim_mw_clipped[i]), 2)
            d_val = round(s_val - b_val, 2)
            p_val = round((d_val / (b_val + 1e-3)) * 100.0, 1) if b_val > 2.0 else 0.0

            intervals.append({
                "time": t_str[-8:-3] if len(t_str) >= 16 else t_str,
                "baseline_mw": b_val,
                "simulated_mw": s_val,
                "delta_mw": d_val,
                "delta_pct": p_val
            })

        return {
            "domain": "solar",
            "entity_name": "Solar Fleet (545 MW)",
            "baseline_params": {
                "capacity_mw": self.baseline_capacity_mw,
                "tilt_deg": self.baseline_tilt,
                "azimuth_deg": self.baseline_azimuth,
                "inverter_capacity_mw": self.baseline_inverter_mw,
                "soiling_loss_pct": self.baseline_soiling_pct
            },
            "simulated_params": {
                "capacity_mw": sim_capacity_mw,
                "tilt_deg": sim_tilt,
                "azimuth_deg": sim_azimuth,
                "inverter_capacity_mw": sim_inverter_mw,
                "soiling_loss_pct": sim_soiling_pct
            },
            "total_baseline_mwh": round(total_baseline_mwh, 1),
            "total_simulated_mwh": round(total_sim_mwh, 1),
            "delta_mwh": round(delta_mwh, 1),
            "yield_change_pct": round(pct_change, 2),
            "intervals": intervals
        }


class FleetWindSimulator:
    """
    Aerodynamics-informed Digital Twin for the 596 MW Wind Fleet (6 farms).
    Computes instantaneous generation impacts when varying:
    - Installed Capacity (MW)
    - Hub Height (m) [uses Hellmann boundary shear power-law]
    - Rotor Pitch Angle Offset (deg) [aerodynamic efficiency derate]
    - Cut-in Wind Speed (m/s)
    - Air Density (kg/m3)
    - Curtailment / Acoustic Derate (%)
    """

    def __init__(self):
        self.baseline_capacity_mw = WIND_FLEET_CAPACITY_MW
        self.baseline_hub_height_m = 100.0
        self.baseline_pitch_deg = 0.0
        self.baseline_cut_in_ms = 3.0
        self.baseline_air_density = 1.225
        self.baseline_derating_pct = 0.0
        self.shear_alpha = 0.143  # Standard IEC wind shear exponent

    def simulate(
        self,
        time_series_df: pd.DataFrame,
        sim_capacity_mw: float = 596.0,
        sim_hub_height_m: float = 100.0,
        sim_pitch_deg: float = 0.0,
        sim_cut_in_ms: float = 3.0,
        sim_air_density: float = 1.225,
        sim_derating_pct: float = 0.0
    ) -> Dict[str, Any]:
        df = time_series_df.copy()
        if "time" in df.columns:
            timestamps = pd.to_datetime(df["time"])
        elif "timestamp" in df.columns:
            timestamps = pd.to_datetime(df["timestamp"])
        else:
            timestamps = pd.date_range("2020-07-01 00:00:00", periods=len(df), freq="15min")

        if "total_power_mw" in df.columns:
            base_mw = df["total_power_mw"].fillna(0.0).values
        elif "generation_mw" in df.columns:
            base_mw = df["generation_mw"].fillna(0.0).values
        else:
            base_mw = np.zeros(len(df))

        # Wind speed reference
        if "windspeed_hub_ms" in df.columns:
            v_ref = df["windspeed_hub_ms"].fillna(7.5).values
        elif "wind_speed_ms" in df.columns:
            v_ref = df["wind_speed_ms"].fillna(7.5).values
        else:
            v_ref = np.clip(np.cbrt(base_mw / (self.baseline_capacity_mw + 1e-3)) * 11.5, 0.0, 25.0)

        # Height boundary shear adjustment: v_sim = v_ref * (h_sim / h_ref)^alpha
        height_ratio = max(0.2, sim_hub_height_m / self.baseline_hub_height_m)
        v_sim = v_ref * (height_ratio ** self.shear_alpha)

        # Air density power adjustment: P ~ rho
        density_ratio = max(0.5, sim_air_density / self.baseline_air_density)

        # Pitch aerodynamic derate: Cp(beta) ~ cos^2(beta) or linear loss
        pitch_efficiency = max(0.0, np.cos(np.radians(max(0.0, sim_pitch_deg))) ** 2.2)

        # Recompute simulated power using aerodynamic cubic curve
        rated_speed = 11.5
        cut_out_speed = 25.0

        sim_mw = np.zeros_like(base_mw)

        # Turbine operating logic
        active_mask = (v_sim >= sim_cut_in_ms) & (v_sim <= cut_out_speed)
        cubic_mask = active_mask & (v_sim < rated_speed)
        rated_mask = active_mask & (v_sim >= rated_speed)

        # Cubic acceleration zone
        sim_mw[cubic_mask] = (
            sim_capacity_mw
            * (((v_sim[cubic_mask] - sim_cut_in_ms) / (rated_speed - sim_cut_in_ms)) ** 3)
            * density_ratio
            * pitch_efficiency
        )

        # Rated plateau zone
        sim_mw[rated_mask] = sim_capacity_mw * density_ratio * pitch_efficiency

        # Apply grid/curtailment derate
        sim_mw = sim_mw * ((100.0 - sim_derating_pct) / 100.0)
        sim_mw = np.clip(sim_mw, 0.0, sim_capacity_mw)

        # Summary KPIs
        total_baseline_mwh = float(np.sum(base_mw) * 0.25)
        total_sim_mwh = float(np.sum(sim_mw) * 0.25)
        delta_mwh = total_sim_mwh - total_baseline_mwh
        pct_change = float((delta_mwh / (total_baseline_mwh + 1e-6)) * 100.0)

        # Build interval output
        interval_count = min(96, len(df))
        step = max(1, len(df) // interval_count)
        indices = list(range(0, len(df), step))[:96]

        intervals = []
        for i in indices:
            t_str = str(timestamps.iloc[i]) if hasattr(timestamps, "iloc") else str(timestamps[i])
            b_val = round(float(base_mw[i]), 2)
            s_val = round(float(sim_mw[i]), 2)
            d_val = round(s_val - b_val, 2)
            p_val = round((d_val / (b_val + 1e-3)) * 100.0, 1) if b_val > 2.0 else 0.0

            intervals.append({
                "time": t_str[-8:-3] if len(t_str) >= 16 else t_str,
                "baseline_mw": b_val,
                "simulated_mw": s_val,
                "delta_mw": d_val,
                "delta_pct": p_val
            })

        return {
            "domain": "wind",
            "entity_name": "Wind Fleet (596 MW)",
            "baseline_params": {
                "capacity_mw": self.baseline_capacity_mw,
                "hub_height_m": self.baseline_hub_height_m,
                "pitch_offset_deg": self.baseline_pitch_deg,
                "cut_in_speed_ms": self.baseline_cut_in_ms,
                "air_density_kg_m3": self.baseline_air_density,
                "derating_pct": self.baseline_derating_pct
            },
            "simulated_params": {
                "capacity_mw": sim_capacity_mw,
                "hub_height_m": sim_hub_height_m,
                "pitch_offset_deg": sim_pitch_deg,
                "cut_in_speed_ms": sim_cut_in_ms,
                "air_density_kg_m3": sim_air_density,
                "derating_pct": sim_derating_pct
            },
            "total_baseline_mwh": round(total_baseline_mwh, 1),
            "total_simulated_mwh": round(total_sim_mwh, 1),
            "delta_mwh": round(delta_mwh, 1),
            "yield_change_pct": round(pct_change, 2),
            "intervals": intervals
        }


# Legacy wrapper for rooftop compatibility if queried
class RooftopSolarSimulator(FleetSolarSimulator):
    pass
