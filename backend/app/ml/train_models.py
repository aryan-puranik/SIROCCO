import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

os.environ["LOKY_MAX_CPU_COUNT"] = "4"

from app.config import DATA_DIR, MODELS_DIR, SOLAR_FLEET_CAPACITY_MW, WIND_FLEET_CAPACITY_MW
from app.ml.feature_store import FeatureStore

class ModelTrainer:
    """
    Trains quantile regression models (P10, P50, P90) for:
    1. Unified Solar Fleet (8 stations combined, 545 MW nominal) incorporating pvlib physics.
    2. Unified Wind Fleet (6 farms combined, 596 MW nominal) incorporating windpowerlib aerodynamics.
    """

    def __init__(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.metrics_summary = {}

    def _train_quantiles(self, X_train, y_train, X_test, y_test, n_estimators=150, learning_rate=0.08):
        """Trains P10, P50, and P90 quantile LightGBM models."""
        models = {}
        predictions = {}

        for q in [0.10, 0.50, 0.90]:
            q_key = f"p{int(q * 100)}"
            model = lgb.LGBMRegressor(
                objective="quantile",
                alpha=q,
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                num_leaves=31,
                random_state=42,
                verbosity=-1,
                n_jobs=4
            )
            model.fit(X_train, y_train)
            models[q_key] = model
            predictions[q_key] = model.predict(X_test)

        # Enforce monotonic quantile order: P10 <= P50 <= P90
        p10 = np.maximum(0.0, predictions["p10"])
        p50 = np.maximum(p10, predictions["p50"])
        p90 = np.maximum(p50, predictions["p90"])

        predictions["p10"] = p10
        predictions["p50"] = p50
        predictions["p90"] = p90

        # Empirical calibration coverage: % of actuals inside [P10, P90]
        y_vals = y_test.values
        inside = (y_vals >= p10) & (y_vals <= p90)
        coverage_pct = float(np.mean(inside) * 100.0)

        # Point forecast metrics (median P50)
        mae = float(mean_absolute_error(y_vals, p50))
        rmse = float(np.sqrt(mean_squared_error(y_vals, p50)))
        r2 = float(r2_score(y_vals, p50))

        metrics = {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 4),
            "p10_p90_coverage_pct": round(coverage_pct, 2),
            "test_samples": len(y_test)
        }

        return models, metrics, predictions

    def train_solar_fleet(self):
        """Train unified Solar Fleet (545 MW nominal) with pvlib physical attributes."""
        parquet_file = DATA_DIR / "combined_solar.parquet"
        print(f"\n[Solar Fleet] Loading {parquet_file.name}...")
        df = pd.read_parquet(parquet_file)

        data, features = FeatureStore.prepare_solar_fleet_features(df)
        target = "total_power_mw"

        # Chronological Split: 2019-01-01 to 2020-06-30 (train), 2020-07-01 to 2020-12-31 (test)
        train_mask = data["time"] < "2020-07-01"
        test_mask = data["time"] >= "2020-07-01"

        X_train, y_train = data.loc[train_mask, features], data.loc[train_mask, target]
        X_test, y_test = data.loc[test_mask, features], data.loc[test_mask, target]

        print(f"Training Solar Fleet on {len(X_train)} samples, testing on {len(X_test)} samples...")
        models, metrics, preds = self._train_quantiles(X_train, y_train, X_test, y_test, n_estimators=150)

        # Daylight MAPE (hours with significant generation)
        daylight_mask = (y_test.values > 15.0)
        if np.sum(daylight_mask) > 0:
            actual_day = y_test.values[daylight_mask]
            pred_day = preds["p50"][daylight_mask]
            daylight_mape = float(np.mean(np.abs(actual_day - pred_day) / actual_day) * 100.0)
        else:
            daylight_mape = 0.0

        metrics["daylight_mape_pct"] = round(daylight_mape, 2)
        metrics["nominal_capacity_mw"] = SOLAR_FLEET_CAPACITY_MW
        metrics["normalized_mae_pct"] = round((metrics["mae"] / SOLAR_FLEET_CAPACITY_MW) * 100.0, 2)
        metrics["status"] = "PASSED" if metrics["normalized_mae_pct"] <= 10.0 else "REVIEW"

        print(f"Solar Fleet Metrics: MAE={metrics['mae']} MW ({metrics['normalized_mae_pct']}% of capacity), R2={metrics['r2']}, Coverage={metrics['p10_p90_coverage_pct']}%")

        feat_importances = models["p50"].feature_importances_
        importance_dict = {
            f: round(float(imp), 4)
            for f, imp in sorted(zip(features, feat_importances), key=lambda x: x[1], reverse=True)
        }
        print("Top 5 Solar Features:", list(importance_dict.items())[:5])

        model_payload = {
            "models": models,
            "features": features,
            "metrics": metrics,
            "feature_importance": importance_dict,
            "site_type": "solar",
            "entity_id": "solar-fleet",
            "nominal_capacity_mw": SOLAR_FLEET_CAPACITY_MW,
            "physics_engine": "pvlib"
        }

        save_path = MODELS_DIR / "solar_fleet.joblib"
        joblib.dump(model_payload, save_path)
        # Also copy/symlink to legacy name for backward compatibility if queried
        joblib.dump(model_payload, MODELS_DIR / "solar_openmeteo.joblib")
        self.metrics_summary["solar_fleet"] = metrics
        return model_payload

    def train_wind_fleet(self):
        """Train unified Wind Fleet (596 MW nominal) with windpowerlib aerodynamic attributes."""
        parquet_file = DATA_DIR / "combined_wind.parquet"
        print(f"\n[Wind Fleet] Loading {parquet_file.name}...")
        df = pd.read_parquet(parquet_file)

        data, features = FeatureStore.prepare_wind_fleet_features(df)
        target = "total_power_mw"

        # Chronological Split: 2019-01-01 to 2020-06-30 (train), 2020-07-01 to 2020-12-31 (test)
        train_mask = data["time"] < "2020-07-01"
        test_mask = data["time"] >= "2020-07-01"

        X_train, y_train = data.loc[train_mask, features], data.loc[train_mask, target]
        X_test, y_test = data.loc[test_mask, features], data.loc[test_mask, target]

        print(f"Training Wind Fleet on {len(X_train)} samples, testing on {len(X_test)} samples...")
        models, metrics, preds = self._train_quantiles(X_train, y_train, X_test, y_test, n_estimators=150)

        metrics["nominal_capacity_mw"] = WIND_FLEET_CAPACITY_MW
        metrics["normalized_mae_pct"] = round((metrics["mae"] / WIND_FLEET_CAPACITY_MW) * 100.0, 2)
        metrics["status"] = "PASSED" if metrics["normalized_mae_pct"] <= 10.0 else "REVIEW"

        print(f"Wind Fleet Metrics: MAE={metrics['mae']} MW ({metrics['normalized_mae_pct']}% of capacity), R2={metrics['r2']}, Coverage={metrics['p10_p90_coverage_pct']}%")

        feat_importances = models["p50"].feature_importances_
        importance_dict = {
            f: round(float(imp), 4)
            for f, imp in sorted(zip(features, feat_importances), key=lambda x: x[1], reverse=True)
        }
        print("Top 5 Wind Features:", list(importance_dict.items())[:5])

        model_payload = {
            "models": models,
            "features": features,
            "metrics": metrics,
            "feature_importance": importance_dict,
            "site_type": "wind",
            "entity_id": "wind-fleet",
            "nominal_capacity_mw": WIND_FLEET_CAPACITY_MW,
            "physics_engine": "windpowerlib"
        }

        save_path = MODELS_DIR / "wind_fleet.joblib"
        joblib.dump(model_payload, save_path)
        # Also copy to legacy names for backward compatibility if queried
        joblib.dump(model_payload, MODELS_DIR / "wind_location1.joblib")
        joblib.dump(model_payload, MODELS_DIR / "wind_location2.joblib")
        self.metrics_summary["wind_fleet"] = metrics
        return model_payload

    def train_all(self):
        """Trains both Solar Fleet and Wind Fleet models and exports metrics summary."""
        print("==================================================")
        print("TRAINING UNIFIED SOLAR & WIND FLEET PREDICTIVE MODELS")
        print("==================================================")
        self.train_solar_fleet()
        self.train_wind_fleet()

        summary_path = MODELS_DIR / "metrics_summary.json"
        with open(summary_path, "w") as f:
            json.dump(self.metrics_summary, f, indent=2)

        print("\nAll fleet models trained and saved to backend/app/ml/models/!")
        return self.metrics_summary

if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train_all()
