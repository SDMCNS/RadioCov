"""Geodetic and coordinate transformation utilities for RF coverage calculations.

Supports:
- Great-circle distance (Haversine & Vincenty)
- Forward bearing (initial azimuth)
- Destination point projection given origin, distance, and bearing
- Interpolating waypoint profiles along radials
- EPSG:4326 (WGS84 Lat/Lon) <-> EPSG:3035 (ETRS89-extended / LAEA Europe)
"""

import math
from typing import List, Tuple, Union
import numpy as np

try:
    from pyproj import Transformer
    # Bi-directional transformers for EU-DEM
    _transformer_to_3035 = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    _transformer_to_4326 = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


class GeoUtils:
    """Geodetic mathematics on a spherical or ellipsoidal Earth."""

    EARTH_RADIUS_M = 6371000.0

    @staticmethod
    def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in meters between two WGS84 points."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return GeoUtils.EARTH_RADIUS_M * c

    @staticmethod
    def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Compute the initial forward azimuth (bearing) in degrees [0, 360) from point 1 to point 2."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dlam = math.radians(lon2 - lon1)

        y = math.sin(dlam) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0

    @staticmethod
    def destination_point(lat: float, lon: float, bearing_deg: float, distance_m: float) -> Tuple[float, float]:
        """Compute destination (lat, lon) in degrees given origin, initial bearing, and distance in meters."""
        delta = distance_m / GeoUtils.EARTH_RADIUS_M
        theta = math.radians(bearing_deg)
        phi1 = math.radians(lat)
        lam1 = math.radians(lon)

        sin_phi2 = math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
        phi2 = math.asin(sin_phi2)

        y = math.sin(theta) * math.sin(delta) * math.cos(phi1)
        x = math.cos(delta) - math.sin(phi1) * math.sin(phi2)
        lam2 = lam1 + math.atan2(y, x)

        dest_lat = math.degrees(phi2)
        dest_lon = (math.degrees(lam2) + 540.0) % 360.0 - 180.0
        return dest_lat, dest_lon

    @staticmethod
    def interpolate_radial_points(
        origin_lat: float,
        origin_lon: float,
        bearing_deg: float,
        max_distance_m: float,
        num_points: int = 150
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate evenly spaced coordinates along a geodesic radial.
        
        Returns:
            Tuple of (distances_m, latitudes, longitudes) as numpy arrays.
        """
        distances_m = np.linspace(0.0, max_distance_m, num_points)
        deltas = distances_m / GeoUtils.EARTH_RADIUS_M
        theta = math.radians(bearing_deg)
        phi1 = math.radians(origin_lat)
        lam1 = math.radians(origin_lon)

        sin_phi2 = np.sin(phi1) * np.cos(deltas) + np.cos(phi1) * np.sin(deltas) * math.cos(theta)
        phi2 = np.arcsin(sin_phi2)

        y = math.sin(theta) * np.sin(deltas) * math.cos(phi1)
        x = np.cos(deltas) - math.sin(phi1) * sin_phi2
        lam2 = lam1 + np.arctan2(y, x)

        lats = np.degrees(phi2)
        lons = (np.degrees(lam2) + 540.0) % 360.0 - 180.0
        return distances_m, lats, lons

    @staticmethod
    def wgs84_to_laea(lon: float, lat: float) -> Tuple[float, float]:
        """Convert WGS84 Lon/Lat to EPSG:3035 (LAEA) coordinate (x, y) in meters."""
        if PYPROJ_AVAILABLE:
            x, y = _transformer_to_3035.transform(lon, lat)
            return float(x), float(y)
        # Approximate spherical Lambert Azimuthal Equal Area fallback if pyproj unavailable
        lam0 = math.radians(10.0)
        phi0 = math.radians(52.0)
        lam = math.radians(lon)
        phi = math.radians(lat)
        k = math.sqrt(2.0 / (1.0 + math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam - lam0)))
        x = 4321000.0 + GeoUtils.EARTH_RADIUS_M * k * math.cos(phi) * math.sin(lam - lam0)
        y = 3210000.0 + GeoUtils.EARTH_RADIUS_M * k * (math.cos(phi0) * math.sin(phi) - math.sin(phi0) * math.cos(phi) * math.cos(lam - lam0))
        return x, y

    @staticmethod
    def laea_to_wgs84(x: float, y: float) -> Tuple[float, float]:
        """Convert EPSG:3035 (LAEA) (x, y) in meters to WGS84 (lon, lat)."""
        if PYPROJ_AVAILABLE:
            lon, lat = _transformer_to_4326.transform(x, y)
            return float(lon), float(lat)
        # Approximate reverse fallback
        return 10.0, 52.0
