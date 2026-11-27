"""Pydantic data models for RadioCov API requests and responses."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from radiocov.config import CUBE_ALTITUDE_STEP_FT, STANDARD_K_FACTOR, FT_TO_METERS, METERS_TO_FT


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    alt_amsl_ft: Optional[float] = Field(default=None, description="Altitude Above Mean Sea Level (AMSL) in feet")
    alt_amsl_m: Optional[float] = Field(default=None, description="Altitude Above Mean Sea Level (AMSL) in meters")


class PointAssessmentRequest(BaseModel):
    tx_lat: float = Field(..., ge=-90.0, le=90.0)
    tx_lon: float = Field(..., ge=-180.0, le=180.0)
    tx_alt_amsl_ft: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (feet)")
    tx_alt_amsl_m: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (meters, fallback)")
    rx_lat: float = Field(..., ge=-90.0, le=90.0)
    rx_lon: float = Field(..., ge=-180.0, le=180.0)
    rx_alt_amsl_ft: Optional[float] = Field(default=None, description="Receiver altitude AMSL (feet)")
    rx_alt_amsl_m: Optional[float] = Field(default=None, description="Receiver altitude AMSL (meters, fallback)")
    frequencies_hz: Union[float, List[float]] = Field(default=1090.0e6, description="Frequency or list of frequencies in Hz")
    k_factor: float = Field(default=STANDARD_K_FACTOR, ge=0.5, le=3.0, description="Atmospheric refraction factor")
    num_profile_points: int = Field(default=200, ge=20, le=1000)
    ignored_obstacle_radius_m: float = Field(default=50.0, ge=0.0, le=500.0, description="Compound ignored obstacle radius in meters (25-100m recommended for station mast compound)")

    def get_tx_alt_ft(self) -> float:
        if self.tx_alt_amsl_ft is not None:
            return float(self.tx_alt_amsl_ft)
        if self.tx_alt_amsl_m is not None:
            return float(self.tx_alt_amsl_m * METERS_TO_FT)
        return 9718.0

    def get_tx_alt_m(self) -> float:
        return self.get_tx_alt_ft() * FT_TO_METERS

    def get_rx_alt_ft(self) -> float:
        if self.rx_alt_amsl_ft is not None:
            return float(self.rx_alt_amsl_ft)
        if self.rx_alt_amsl_m is not None:
            return float(self.rx_alt_amsl_m * METERS_TO_FT)
        return 3000.0

    def get_rx_alt_m(self) -> float:
        return self.get_rx_alt_ft() * FT_TO_METERS


class RadialProfileRequest(BaseModel):
    tx_lat: float = Field(..., ge=-90.0, le=90.0)
    tx_lon: float = Field(..., ge=-180.0, le=180.0)
    tx_alt_amsl_ft: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (feet)")
    tx_alt_amsl_m: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (meters, fallback)")
    bearing_deg: float = Field(..., ge=0.0, le=360.0, description="Azimuth angle in degrees [0, 360)")
    max_distance_km: float = Field(default=100.0, ge=1.0, le=500.0)
    target_alt_amsl_ft: Optional[float] = Field(default=None, description="Target altitude AMSL in feet (e.g. 8000 ft)")
    target_alt_amsl_m: Optional[float] = Field(default=None, description="Target altitude AMSL in meters (fallback)")
    frequency_hz: float = Field(default=1000.0e6, gt=0)
    k_factor: float = Field(default=STANDARD_K_FACTOR, ge=0.5, le=3.0)
    num_profile_points: int = Field(default=250, ge=50, le=1000)
    ignored_obstacle_radius_m: float = Field(default=50.0, ge=0.0, le=500.0, description="Compound ignored obstacle radius in meters (25-100m)")

    def get_tx_alt_ft(self) -> float:
        if self.tx_alt_amsl_ft is not None:
            return float(self.tx_alt_amsl_ft)
        if self.tx_alt_amsl_m is not None:
            return float(self.tx_alt_amsl_m * METERS_TO_FT)
        return 9718.0

    def get_tx_alt_m(self) -> float:
        return self.get_tx_alt_ft() * FT_TO_METERS

    def get_target_alt_ft(self) -> float:
        if self.target_alt_amsl_ft is not None:
            return float(self.target_alt_amsl_ft)
        if self.target_alt_amsl_m is not None:
            return float(self.target_alt_amsl_m * METERS_TO_FT)
        return 8000.0

    def get_target_alt_m(self) -> float:
        return self.get_target_alt_ft() * FT_TO_METERS


class HorizontalSliceRequest(BaseModel):
    tx_lat: float = Field(..., ge=-90.0, le=90.0)
    tx_lon: float = Field(..., ge=-180.0, le=180.0)
    tx_alt_amsl_ft: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (feet)")
    tx_alt_amsl_m: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (meters, fallback)")
    alt_ft: float = Field(default=8000.0, ge=0.0, le=100000.0, description="Horizontal slice altitude in feet AMSL")
    frequency_hz: float = Field(default=1000.0e6, gt=0)
    max_range_km: float = Field(default=100.0, ge=5.0, le=400.0)
    num_radials: int = Field(default=72, ge=24, le=360)
    range_step_km: float = Field(default=2.5, ge=0.5, le=10.0)
    k_factor: float = Field(default=STANDARD_K_FACTOR, ge=0.5, le=3.0)
    ignored_obstacle_radius_m: float = Field(default=50.0, ge=0.0, le=500.0, description="Compound ignored obstacle radius in meters (25-100m)")

    def get_tx_alt_ft(self) -> float:
        if self.tx_alt_amsl_ft is not None:
            return float(self.tx_alt_amsl_ft)
        if self.tx_alt_amsl_m is not None:
            return float(self.tx_alt_amsl_m * METERS_TO_FT)
        return 9718.0

    def get_tx_alt_m(self) -> float:
        return self.get_tx_alt_ft() * FT_TO_METERS


class VolumetricCubesRequest(BaseModel):
    tx_lat: float = Field(..., ge=-90.0, le=90.0)
    tx_lon: float = Field(..., ge=-180.0, le=180.0)
    tx_alt_amsl_ft: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (feet)")
    tx_alt_amsl_m: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (meters, fallback)")
    max_range_km: float = Field(default=100.0, ge=5.0, le=300.0)
    min_alt_ft: float = Field(default=1000.0, ge=0.0, description="Minimum airspace altitude (feet AMSL)")
    max_alt_ft: float = Field(default=20000.0, ge=1000.0, description="Maximum airspace altitude (feet AMSL)")
    alt_step_ft: float = Field(default=CUBE_ALTITUDE_STEP_FT, ge=100.0, le=5000.0, description="Voxel height step (default 1000 ft)")
    freq_min_hz: float = Field(default=100.0e6, gt=0, description="Minimum frequency in Hz")
    freq_max_hz: float = Field(default=2000.0e6, gt=0, description="Maximum frequency in Hz")
    freq_step_hz: float = Field(default=500.0e6, gt=0, description="Frequency increment in Hz")
    num_radials: int = Field(default=48, ge=12, le=120)
    range_step_km: float = Field(default=3.0, ge=1.0, le=10.0)
    k_factor: float = Field(default=STANDARD_K_FACTOR, ge=0.5, le=3.0)
    ignored_obstacle_radius_m: float = Field(default=50.0, ge=0.0, le=500.0, description="Compound ignored obstacle radius in meters (25-100m)")

    def get_tx_alt_ft(self) -> float:
        if self.tx_alt_amsl_ft is not None:
            return float(self.tx_alt_amsl_ft)
        if self.tx_alt_amsl_m is not None:
            return float(self.tx_alt_amsl_m * METERS_TO_FT)
        return 9718.0

    def get_tx_alt_m(self) -> float:
        return self.get_tx_alt_ft() * FT_TO_METERS


class PointCloud3DRequest(BaseModel):
    tx_lat: float = Field(..., ge=-90.0, le=90.0)
    tx_lon: float = Field(..., ge=-180.0, le=180.0)
    tx_alt_amsl_ft: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (feet)")
    tx_alt_amsl_m: Optional[float] = Field(default=None, description="Transmitter altitude AMSL (meters, fallback)")
    max_range_km: float = Field(default=80.0, ge=5.0, le=250.0)
    min_alt_ft: float = Field(default=1000.0, ge=0.0)
    max_alt_ft: float = Field(default=20000.0, ge=1000.0)
    alt_step_ft: float = Field(default=CUBE_ALTITUDE_STEP_FT)
    frequency_hz: float = Field(default=1000.0e6, gt=0)
    num_radials: int = Field(default=36, ge=12, le=72)
    range_step_km: float = Field(default=4.0, ge=1.0, le=10.0)
    k_factor: float = Field(default=STANDARD_K_FACTOR)
    subsample_step: int = Field(default=1, ge=1, le=4)
    ignored_obstacle_radius_m: float = Field(default=50.0, ge=0.0, le=500.0, description="Compound ignored obstacle radius in meters (25-100m)")

    def get_tx_alt_ft(self) -> float:
        if self.tx_alt_amsl_ft is not None:
            return float(self.tx_alt_amsl_ft)
        if self.tx_alt_amsl_m is not None:
            return float(self.tx_alt_amsl_m * METERS_TO_FT)
        return 9718.0

    def get_tx_alt_m(self) -> float:
        return self.get_tx_alt_ft() * FT_TO_METERS
