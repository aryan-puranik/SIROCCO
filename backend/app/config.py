import os
from pathlib import Path

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
MODELS_DIR = BACKEND_DIR / "app" / "ml" / "models"
RAW_DATA_DIR = PROJECT_ROOT

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
SQLITE_DB_PATH = DATA_DIR / "sirocco.db"
DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH.as_posix()}"
SYNC_DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

# Asset Default Specs
SOLAR_FLEET_CAPACITY_MW = 545.0  # 8 solar stations combined
WIND_FLEET_CAPACITY_MW = 596.0   # 6 wind farms combined
TOTAL_GRID_CAPACITY_MW = 1141.0  # 1,141 MW total fleet capacity

WIND_NAMEPLATE_MW = 596.0
SOLAR_OPENMETEO_CAPACITY_MW = 545.0
SOLAR_ROOFTOP_CAPACITY_MW = 545.0

# CORS Settings
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"
]
