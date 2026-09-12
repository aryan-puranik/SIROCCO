import numpy as np
import pandas as pd
import pvlib

class FeatureStore:
    """
    Domain-specific feature engineering for Wind and Solar generation models.
    Preserves exact physical equations, circular encodings, and solar geometries.
    """

    @staticmethod
    def prepare_wind_features(df: pd.DataFrame, is_training: bool = True) -> tuple[pd.DataFrame, list[str]]:
        """
        Engineers physics and circular features for wind turbine assets (Location1 & Location2).
        Target: 'Power' (capacity factor 0.0 - 1.0).
        """
        data = df.copy()

        # Parse timestamps
        if "Time" in data.columns and not np.issubdtype(data["Time"].dtype, np.datetime64):
            data["Time"] = pd.to_datetime(data["Time"])

        # Boundary-layer wind shear: windspeed_100m / windspeed_10m
        data["wind_shear"] = data["windspeed_100m"] / (data["windspeed_10m"] + 1e-3)

        # Circular encoding for wind directions (0-360 degrees)
        rad_10m = np.radians(data["winddirection_10m"])
        rad_100m = np.radians(data["winddirection_100m"])
        data["wind_dir_sin_10m"] = np.sin(rad_10m)
        data["wind_dir_cos_10m"] = np.cos(rad_10m)
        data["wind_dir_sin_100m"] = np.sin(rad_100m)
        data["wind_dir_cos_100m"] = np.cos(rad_100m)

        # Physics-informed power curve feature: velocity cubed
        data["windspeed_100m_cubed"] = data["windspeed_100m"] ** 3

        # Calendar features
        if "Time" in data.columns:
            data["hour"] = data["Time"].dt.hour
            data["month"] = data["Time"].dt.month
            data["day_of_year"] = data["Time"].dt.dayofyear
        else:
            data["hour"] = 12
            data["month"] = 6
            data["day_of_year"] = 180

        feature_cols = [
            "temperature_2m",
            "relativehumidity_2m",
            "dewpoint_2m",
            "windspeed_10m",
            "windspeed_100m",
            "windgusts_10m",
            "wind_shear",
            "wind_dir_sin_10m",
            "wind_dir_cos_10m",
            "wind_dir_sin_100m",
            "wind_dir_cos_100m",
            "windspeed_100m_cubed",
            "hour",
            "month",
            "day_of_year"
        ]

        return data, feature_cols

    @staticmethod
    def prepare_solar_openmeteo_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        Engineers features for the 3-year hourly Solar PV asset (pv-forecast-openmeteo).
        Target: 'avg W' (power in Watts, 0 - 5068 W).
        """
        data = df.copy()

        if "time" in data.columns and not np.issubdtype(data["time"].dtype, np.datetime64):
            data["time"] = pd.to_datetime(data["time"])

        # Temperature conversion from Kelvin to Celsius
        data["temp_c"] = data["temp"] - 273.15

        # Circular wind direction
        rad_wind = np.radians(data["wind_deg"])
        data["wind_deg_sin"] = np.sin(rad_wind)
        data["wind_deg_cos"] = np.cos(rad_wind)

        # Time features
        if "time" in data.columns:
            data["hour"] = data["time"].dt.hour
            data["month"] = data["time"].dt.month
            if "day_of_year" not in data.columns:
                data["day_of_year"] = data["time"].dt.dayofyear

        # Clearsky theoretical index / ratio
        data["clearsky_w"] = data["clear_sky"].astype(float)
        data["clearsky_ratio"] = data["clearsky_w"] / (data["clearsky_w"].max() + 1e-3)
        data["cloud_damping"] = (100.0 - data["clouds_all"]) / 100.0

        feature_cols = [
            "temp_c",
            "humidity",
            "pressure",
            "clouds_all",
            "wind_speed",
            "wind_deg_sin",
            "wind_deg_cos",
            "clearsky_w",
            "clearsky_ratio",
            "cloud_damping",
            "hour",
            "month",
            "day_of_year"
        ]

        return data, feature_cols

    @staticmethod
    def prepare_solar_rooftop_features(df: pd.DataFrame, lat: float = 23.0225, lon: float = 72.5714) -> tuple[pd.DataFrame, list[str]]:
        """
        Derives solar geometry and clear-sky irradiance for rooftop solar demo asset.
        Target: 'forecast_energy_wh_15min'.
        """
        data = df.copy()

        if "timestamp" in data.columns and not np.issubdtype(data["timestamp"].dtype, np.datetime64):
            data["timestamp"] = pd.to_datetime(data["timestamp"])

        # Derive solar position using pvlib
        solpos = pvlib.solarposition.get_solarposition(data["timestamp"], lat, lon)
        data["solar_zenith_deg"] = solpos["zenith"].values
        data["solar_azimuth_deg"] = solpos["azimuth"].values
        data["cos_zenith"] = np.maximum(0.0, np.cos(np.radians(data["solar_zenith_deg"])))

        # Simplified clearsky GHI estimate (Haurwitz model approximation)
        data["clearsky_ghi"] = np.maximum(0.0, 1090.0 * np.exp(-0.057 / (data["cos_zenith"] + 1e-3)) * data["cos_zenith"])

        data["hour"] = data["timestamp"].dt.hour
        data["minute"] = data["timestamp"].dt.minute
        data["day_of_year"] = data["timestamp"].dt.dayofyear
        data["month"] = data["timestamp"].dt.month

        feature_cols = [
            "solar_zenith_deg",
            "solar_azimuth_deg",
            "cos_zenith",
            "clearsky_ghi",
            "hour",
            "minute",
            "day_of_year",
            "month"
        ]

        return data, feature_cols

    @staticmethod
    def prepare_solar_fleet_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        Feature engineering for combined Solar Fleet (545 MW nominal, 8 stations).
        Target: 'total_power_mw'.
        Incorporates pvlib physics calculations, solar geometry, and weather attributes.
        """
        data = df.copy()
        if "time" in data.columns and not np.issubdtype(data["time"].dtype, np.datetime64):
            data["time"] = pd.to_datetime(data["time"])

        if "total_power_mw" in data.columns:
            data["power_lag_1"] = data["total_power_mw"].shift(1).bfill()
            data["power_lag_4"] = data["total_power_mw"].shift(4).bfill()
            data["power_lag_96"] = data["total_power_mw"].shift(96).bfill()
            data["power_rolling_4"] = data["total_power_mw"].shift(1).rolling(4, min_periods=1).mean()
        elif "power_mw" in data.columns:
            data["power_lag_1"] = data["power_mw"].shift(1).bfill()
            data["power_lag_4"] = data["power_mw"].shift(4).bfill()
            data["power_lag_96"] = data["power_mw"].shift(96).bfill()
            data["power_rolling_4"] = data["power_mw"].shift(1).rolling(4, min_periods=1).mean()

        if "time" in data.columns:
            data["hour"] = data["time"].dt.hour
            data["month"] = data["time"].dt.month
            data["day_of_year"] = data["time"].dt.dayofyear
            data["minute"] = data["time"].dt.minute
        else:
            data["hour"] = 12
            data["month"] = 6
            data["day_of_year"] = 180
            data["minute"] = 0

        # Physical POA / GHI ratio
        if "ghi_w_m2" in data.columns and "pvlib_physics_power_mw" in data.columns:
            data["irradiance_clearsky_proxy"] = data["ghi_w_m2"] / (data["ghi_w_m2"].max() + 1e-3)
        else:
            data["irradiance_clearsky_proxy"] = 0.5

        feature_cols = [
            "pvlib_physics_power_mw",
            "ghi_w_m2",
            "dni_w_m2",
            "temperature_c",
            "pressure_hpa",
            "humidity_pct",
            "power_lag_1",
            "power_lag_4",
            "power_lag_96",
            "power_rolling_4",
            "hour",
            "minute",
            "month",
            "day_of_year"
        ]

        # Ensure all columns exist
        for col in feature_cols:
            if col not in data.columns:
                data[col] = 0.0

        return data, feature_cols

    @staticmethod
    def prepare_wind_fleet_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        Feature engineering for combined Wind Fleet (596 MW nominal, 6 farms).
        Target: 'total_power_mw'.
        Incorporates windpowerlib aerodynamic calculations, shear, density, and direction encodings.
        """
        data = df.copy()
        if "time" in data.columns and not np.issubdtype(data["time"].dtype, np.datetime64):
            data["time"] = pd.to_datetime(data["time"])

        if "total_power_mw" in data.columns:
            data["power_lag_1"] = data["total_power_mw"].shift(1).bfill()
            data["power_lag_4"] = data["total_power_mw"].shift(4).bfill()
            data["power_rolling_4"] = data["total_power_mw"].shift(1).rolling(4, min_periods=1).mean()
        elif "power_mw" in data.columns:
            data["power_lag_1"] = data["power_mw"].shift(1).bfill()
            data["power_lag_4"] = data["power_mw"].shift(4).bfill()
            data["power_rolling_4"] = data["power_mw"].shift(1).rolling(4, min_periods=1).mean()

        # Wind directions circular encoding
        if "winddirection_hub_deg" in data.columns:
            rad_hub = np.radians(data["winddirection_hub_deg"])
            data["wind_dir_sin"] = np.sin(rad_hub)
            data["wind_dir_cos"] = np.cos(rad_hub)
        else:
            data["wind_dir_sin"] = 0.0
            data["wind_dir_cos"] = 1.0

        # Wind speed cubed
        if "windspeed_hub_ms" in data.columns:
            data["windspeed_hub_cubed"] = data["windspeed_hub_ms"] ** 3
        else:
            data["windspeed_hub_cubed"] = 0.0

        if "time" in data.columns:
            data["hour"] = data["time"].dt.hour
            data["month"] = data["time"].dt.month
            data["day_of_year"] = data["time"].dt.dayofyear
        else:
            data["hour"] = 12
            data["month"] = 6
            data["day_of_year"] = 180

        feature_cols = [
            "windpowerlib_physics_power_mw",
            "windspeed_hub_ms",
            "windspeed_hub_cubed",
            "windspeed_10m_ms",
            "windspeed_30m_ms",
            "windspeed_50m_ms",
            "wind_shear",
            "wind_dir_sin",
            "wind_dir_cos",
            "air_density_kg_m3",
            "temperature_c",
            "pressure_hpa",
            "humidity_pct",
            "power_lag_1",
            "power_lag_4",
            "power_rolling_4",
            "hour",
            "month",
            "day_of_year"
        ]

        # Ensure all columns exist
        for col in feature_cols:
            if col not in data.columns:
                data[col] = 0.0

        return data, feature_cols
