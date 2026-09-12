from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.db import Base

class Site(Base):
    __tablename__ = "sites"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)  # 'wind' or 'solar'
    capacity_mw = Column(Float, nullable=False)
    timezone = Column(String(64), default="UTC")
    location_name = Column(String(128), default="Site Location")
    status = Column(String(32), default="operational")  # operational, degraded, maintenance
    current_generation_mw = Column(Float, default=0.0)
    health_score = Column(Float, default=98.5)
    metadata_json = Column(Text, nullable=True)

    time_series = relationship("TimeSeriesData", back_populates="site", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="site", cascade="all, delete-orphan")

class TimeSeriesData(Base):
    __tablename__ = "time_series_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False, index=True)
    site_id = Column(String(64), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    generation_mw = Column(Float, nullable=False)
    
    # Common & Wind Features
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    dewpoint_c = Column(Float, nullable=True)
    wind_speed_ms = Column(Float, nullable=True)
    windspeed_100m_ms = Column(Float, nullable=True)
    winddirection_10m_deg = Column(Float, nullable=True)
    winddirection_100m_deg = Column(Float, nullable=True)
    windgusts_10m_ms = Column(Float, nullable=True)

    # Solar Features
    ghi_w_m2 = Column(Float, nullable=True)
    cloud_cover_total_pct = Column(Float, nullable=True)
    cloud_cover_high_pct = Column(Float, nullable=True)
    cloud_cover_mid_pct = Column(Float, nullable=True)
    cloud_cover_low_pct = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    snowfall_cm = Column(Float, nullable=True)
    mslp_hpa = Column(Float, nullable=True)
    solar_zenith_deg = Column(Float, nullable=True)
    solar_azimuth_deg = Column(Float, nullable=True)
    angle_of_incidence_deg = Column(Float, nullable=True)
    clearsky_w = Column(Float, nullable=True)

    data_quality_flag = Column(String(32), default="valid")

    site = relationship("Site", back_populates="time_series")

    __table_args__ = (
        Index("ix_site_time", "site_id", "time"),
    )

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(64), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    target_time = Column(DateTime, nullable=False, index=True)
    p10_mw = Column(Float, nullable=False)
    p50_mw = Column(Float, nullable=False)
    p90_mw = Column(Float, nullable=False)
    actual_mw = Column(Float, nullable=True)
    model_version = Column(String(64), default="v1.0")

    site = relationship("Site", back_populates="forecasts")

    __table_args__ = (
        Index("ix_forecast_site_target", "site_id", "target_time"),
    )

class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False, index=True)
    site_id = Column(String(64), nullable=False)
    metric_name = Column(String(64), nullable=False)
    metric_value = Column(Float, nullable=False)
    target_value = Column(Float, nullable=True)
    status = Column(String(32), default="PASSED")
    split_type = Column(String(32), default="test")
    evaluated_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(64), nullable=False, index=True)
    site_name = Column(String(128), nullable=False)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)  # CRITICAL, WARNING, INFO
    message = Column(Text, nullable=False)
    diagnostic_details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), default="ACTIVE")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(64), nullable=False, index=True)
    site_name = Column(String(128), nullable=False)
    recommendation_type = Column(String(64), nullable=False)
    action = Column(String(256), nullable=False)
    rationale = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    impact_mw = Column(Float, default=0.0)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
