"""Terrain Provider Interface for sampling European EU-DEM GeoTIFF and synthetic terrain.

Provides:
- Thread-safe, windowed raster sampling from the EU-DEM 25m GeoTIFF (EPSG:3035)
- Radial elevation profile extraction with LRU caching
- Out-of-bounds sea-level / synthetic terrain handling
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import rasterio
    from rasterio.windows import from_bounds
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

from radiocov.config import DEFAULT_DEM_TIFF
from radiocov.core.geo import GeoUtils


class TerrainProvider:
    """Provides high-performance ground elevation queries for RF propagation."""

    def __init__(self, tiff_path: Optional[Union[str, Path]] = None):
        self.tiff_path = Path(tiff_path) if tiff_path else DEFAULT_DEM_TIFF
        self._dataset = None
        self._lock = threading.Lock()
        self._profile_cache: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
        self.is_dem_available = False

        if RASTERIO_AVAILABLE and self.tiff_path.exists():
            try:
                self._dataset = rasterio.open(str(self.tiff_path))
                self.bounds = self._dataset.bounds
                self.transform = self._dataset.transform
                self.nodata = self._dataset.nodata
                self.is_dem_available = True
            except Exception as e:
                print(f"[RadioCov] Warning: Failed to open DEM GeoTIFF at {self.tiff_path}: {e}")

    def close(self):
        """Close dataset file handle."""
        with self._lock:
            if self._dataset and not self._dataset.closed:
                self._dataset.close()
                self._dataset = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_elevation_at_point(self, lat: float, lon: float) -> float:
        """Get ground elevation in meters AMSL at a single (lat, lon) point."""
        return self.get_elevations([(lat, lon)])[0]

    def get_elevations(self, lat_lons: List[Tuple[float, float]]) -> List[float]:
        """Sample ground elevations for a list of (lat, lon) tuples in meters AMSL."""
        if not lat_lons:
            return []

        results = [0.0] * len(lat_lons)
        if not self.is_dem_available or not self._dataset:
            return results

        # Convert WGS84 to EPSG:3035 LAEA
        coords_laea = [GeoUtils.wgs84_to_laea(lon, lat) for lat, lon in lat_lons]
        valid_indices = []
        valid_coords = []

        for idx, (x, y) in enumerate(coords_laea):
            if (self.bounds.left <= x <= self.bounds.right) and (self.bounds.bottom <= y <= self.bounds.top):
                valid_indices.append(idx)
                valid_coords.append((x, y))

        if not valid_coords:
            return results

        with self._lock:
            try:
                samples = list(self._dataset.sample(valid_coords))
                for idx, val in zip(valid_indices, samples):
                    try:
                        elev = float(val[0])
                        if np.isnan(elev) or (self.nodata is not None and elev == self.nodata) or elev < -500.0:
                            elev = 0.0
                        results[idx] = max(0.0, elev)
                    except Exception:
                        results[idx] = 0.0
            except Exception:
                pass

        return results

    def get_radial_profile(
        self,
        origin_lat: float,
        origin_lon: float,
        bearing_deg: float,
        max_distance_m: float,
        num_points: int = 150,
        use_cache: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Extract terrain cross-section along a geodesic radial from origin.
        
        Returns:
            Tuple of:
            - distances_m: Array of distances along radial from 0 to max_distance_m
            - lats: Array of latitudes
            - lons: Array of longitudes
            - ground_elevations_m: Array of terrain elevations AMSL in meters
        """
        cache_key = f"{origin_lat:.4f}_{origin_lon:.4f}_{bearing_deg:.1f}_{max_distance_m:.0f}_{num_points}"
        if use_cache and cache_key in self._profile_cache:
            return self._profile_cache[cache_key]

        distances_m, lats, lons = GeoUtils.interpolate_radial_points(
            origin_lat, origin_lon, bearing_deg, max_distance_m, num_points
        )

        lat_lon_pairs = list(zip(lats, lons))
        elevs = self.get_elevations(lat_lon_pairs)
        ground_elevations_m = np.array(elevs, dtype=np.float64)

        result = (distances_m, lats, lons, ground_elevations_m)
        if use_cache:
            if len(self._profile_cache) > 2000:
                self._profile_cache.clear()
            self._profile_cache[cache_key] = result

        return result
