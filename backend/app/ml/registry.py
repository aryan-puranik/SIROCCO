import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from app.config import MODELS_DIR

class ModelRegistry:
    """Manages loaded ML models, caching, and quantile inference."""

    _instance = None
    _models: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._load_all_models()
        return cls._instance

    def _load_all_models(self):
        """Preloads saved models into memory for fast zero-latency inference."""
        model_files = {
            "solar_fleet": "solar_fleet.joblib",
            "wind_fleet": "wind_fleet.joblib",
            "wind_location1": "wind_location1.joblib",
            "wind_location2": "wind_location2.joblib",
            "solar_openmeteo": "solar_openmeteo.joblib",
            "solar_rooftop": "solar_rooftop.joblib"
        }

        for key, filename in model_files.items():
            path = MODELS_DIR / filename
            if path.exists():
                try:
                    self._models[key] = joblib.load(path)
                except Exception as e:
                    print(f"Error loading {key}: {e}")

    def get_model(self, model_key: str) -> Optional[Dict[str, Any]]:
        return self._models.get(model_key)

    def predict_quantiles(self, model_key: str, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Runs inference and returns P10, P50, and P90 predictions,
        guaranteeing monotonic ordering P10 <= P50 <= P90.
        """
        payload = self.get_model(model_key)
        if not payload:
            raise ValueError(f"Model '{model_key}' not found in registry.")

        features = payload["features"]
        models = payload["models"]

        # Ensure all expected columns are present
        for f in features:
            if f not in X.columns:
                X[f] = 0.0

        X_input = X[features]
        p10 = models["p10"].predict(X_input)
        p50 = models["p50"].predict(X_input)
        p90 = models["p90"].predict(X_input)

        # Monotonicity clip
        p10 = np.maximum(0.0, p10)
        p50 = np.maximum(p10, p50)
        p90 = np.maximum(p50, p90)

        return {
            "p10": p10,
            "p50": p50,
            "p90": p90
        }
