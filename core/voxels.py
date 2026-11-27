"""Volumetric 1,000-ft Airspace Cube Coverage and Slicing Engine.

Generates 3D voxel datasets of RF coverage and provides:
- Horizontal coverage slices (at user-selected 1,000-ft altitudes)
- Vertical cross-sections (along any azimuth bearing)
- Elevation / angular coverage diagrams
- 3D voxel mesh / point cloud for WebGL 3D rendering
- Multi-frequency sweep comparison across the radio spectrum
"""

from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from radiocov.config import (
    FT_TO_METERS,
    METERS_TO_FT,
    CUBE_ALTITUDE_STEP_FT,
    STANDARD_K_FACTOR,
)
from radiocov.core.physics import RFPhysics
from radiocov.core.geo import GeoUtils
from radiocov.core.terrain import TerrainProvider
from radiocov.core.engine import RFCoverageEngine


class SliceType(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    VOLUMETRIC_3D = "volumetric_3d"
    FREQUENCY_SWEEP = "frequency_sweep"


class VolumetricCoverageGrid:
    """Manages 3D grid of 1,000-ft cubes for RF Line of Sight and propagation."""

    def __init__(
        self,
        engine: RFCoverageEngine,
        tx_lat: float,
        tx_lon: float,
        tx_alt_amsl_m: Optional[float] = None,
        max_range_km: float = 150.0,
        min_alt_ft: float = 1000.0,
        max_alt_ft: float = 30000.0,
        alt_step_ft: float = CUBE_ALTITUDE_STEP_FT,
        num_radials: int = 72,  # every 5 degrees by default
        range_step_km: float = 2.5,
        k_factor: float = STANDARD_K_FACTOR,
        ignored_obstacle_radius_m: float = 50.0,
        tx_alt_amsl_ft: Optional[float] = None,
    ):
        self.engine = engine
        self.tx_lat = tx_lat
        self.tx_lon = tx_lon
        if tx_alt_amsl_ft is not None:
            self.tx_alt_amsl_m = float(tx_alt_amsl_ft) * FT_TO_METERS
            self.tx_alt_amsl_ft = float(tx_alt_amsl_ft)
        elif tx_alt_amsl_m is not None:
            self.tx_alt_amsl_m = float(tx_alt_amsl_m)
            self.tx_alt_amsl_ft = float(tx_alt_amsl_m) * METERS_TO_FT
        else:
            self.tx_alt_amsl_m = 2962.0
            self.tx_alt_amsl_ft = 9718.0

        self.max_range_km = max_range_km
        self.min_alt_ft = min_alt_ft
        self.max_alt_ft = max_alt_ft
        self.alt_step_ft = alt_step_ft
        self.num_radials = num_radials
        self.range_step_km = range_step_km
        self.k_factor = k_factor
        self.ignored_obstacle_radius_m = float(ignored_obstacle_radius_m)

        # 1D coordinates
        self.altitude_levels_ft = np.arange(min_alt_ft, max_alt_ft + (alt_step_ft / 2.0), alt_step_ft)
        self.altitude_levels_m = self.altitude_levels_ft * FT_TO_METERS
        self.azimuths_deg = np.linspace(0.0, 360.0, num_radials, endpoint=False)
        self.distances_km = np.arange(range_step_km, max_range_km + (range_step_km / 2.0), range_step_km)

        self.n_alts = len(self.altitude_levels_ft)
        self.n_radials = len(self.azimuths_deg)
        self.n_ranges = len(self.distances_km)

        # Pre-calculated radial terrain profiles cache
        # radial_idx -> (distances_m, lats, lons, terrain_elev_m, earth_bulge_m)
        self._radial_terrain_cache: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}

    def _get_or_compute_radial(self, radial_idx: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Retrieve or compute the terrain profile and Earth bulge along a specific azimuth radial."""
        if radial_idx in self._radial_terrain_cache:
            return self._radial_terrain_cache[radial_idx]

        bearing = float(self.azimuths_deg[radial_idx])
        # High-resolution sampling along radial: at least 300 points, or 100m sample spacing
        num_samples = max(300, int(self.max_range_km / 0.1))
        max_dist_m = self.max_range_km * 1000.0

        dists_m, lats, lons, terrain_m = self.engine.terrain.get_radial_profile(
            self.tx_lat, self.tx_lon, bearing, max_dist_m, num_points=num_samples
        )

        d1 = dists_m
        d2 = max_dist_m - dists_m
        bulge_m = RFPhysics.earth_bulge(d1, d2, k_factor=self.k_factor)

        data = (dists_m, lats, lons, terrain_m, bulge_m)
        self._radial_terrain_cache[radial_idx] = data
        return data

    def compute_coverage_cube_matrix(
        self,
        frequencies_hz: Union[float, List[float]]
    ) -> Dict[str, Any]:
        """Compute the full 3D volumetric coverage grid across altitudes and radials.
        
        Returns:
            Dictionary with 3D status matrices for each frequency, metadata, and axes.
        """
        freq_list = [frequencies_hz] if isinstance(frequencies_hz, (int, float)) else list(frequencies_hz)

        # 3D arrays: shape (n_radials, n_ranges, n_alts)
        # Store boolean LoS and path loss for each frequency
        results_by_freq = {
            f: {
                "los_matrix": np.zeros((self.n_radials, self.n_ranges, self.n_alts), dtype=bool),
                "path_loss_db": np.zeros((self.n_radials, self.n_ranges, self.n_alts), dtype=np.float32),
                "clearance_ratio": np.zeros((self.n_radials, self.n_ranges, self.n_alts), dtype=np.float32)
            }
            for f in freq_list
        }

        min_clearance_matrix = np.zeros((self.n_radials, self.n_ranges, self.n_alts), dtype=np.float32)

        # Process radial by radial for maximum speed and memory efficiency
        for r_idx in range(self.n_radials):
            dists_m, lats, lons, terrain_m, _ = self._get_or_compute_radial(r_idx)

            for d_idx, dist_km in enumerate(self.distances_km):
                target_dist_m = dist_km * 1000.0
                # Accurate ground elevation at exact target distance via linear interpolation
                target_ground_m = float(np.interp(target_dist_m, dists_m, terrain_m))

                # Profile sample points up to target distance
                prof_mask = (dists_m <= target_dist_m)
                p_dists = dists_m[prof_mask]
                p_terr = terrain_m[prof_mask]

                # Ensure exact target distance is present at the end of the profile slice
                if len(p_dists) > 0 and (target_dist_m - p_dists[-1]) > 5.0:
                    p_dists = np.append(p_dists, target_dist_m)
                    p_terr = np.append(p_terr, target_ground_m)

                if len(p_dists) < 2:
                    continue

                d1 = p_dists
                d2 = target_dist_m - p_dists
                # True path-specific earth bulge for this target distance
                bulge = RFPhysics.earth_bulge(d1, d2, k_factor=self.k_factor)
                eff_terrain = p_terr + bulge

                # Inner path mask (excluding antenna base and immediate receiver point)
                # Apply compound / DEM alignment tolerance radius around transmitter mast (25-100m)
                min_tx_d = max(1.0, self.ignored_obstacle_radius_m)
                max_rx_d = max(min_tx_d + 10.0, target_dist_m - 50.0)
                inner_idx = (p_dists > min_tx_d) & (p_dists < max_rx_d)

                for a_idx, alt_m in enumerate(self.altitude_levels_m):
                    rx_above_ground = bool(alt_m > target_ground_m)

                    if not rx_above_ground:
                        # Target voxel is underground inside terrain
                        min_clearance_matrix[r_idx, d_idx, a_idx] = float(alt_m - target_ground_m)
                        for f_hz in freq_list:
                            results_by_freq[f_hz]["los_matrix"][r_idx, d_idx, a_idx] = False
                            results_by_freq[f_hz]["path_loss_db"][r_idx, d_idx, a_idx] = 250.0
                            results_by_freq[f_hz]["clearance_ratio"][r_idx, d_idx, a_idx] = -99.0
                        continue

                    # Direct LoS ray at distance d: h(d) = tx_alt + (d / target_dist) * (alt_m - tx_alt)
                    t_frac = p_dists / target_dist_m
                    ray_m = self.tx_alt_amsl_m + t_frac * (alt_m - self.tx_alt_amsl_m)

                    if np.any(inner_idx):
                        clearances = ray_m[inner_idx] - eff_terrain[inner_idx]
                        geom_min_clear = float(np.min(clearances))
                        inner_d1 = p_dists[inner_idx]
                        inner_d2 = target_dist_m - inner_d1
                    else:
                        clearances = np.array([alt_m - target_ground_m])
                        geom_min_clear = float(alt_m - target_ground_m)
                        inner_d1 = np.array([target_dist_m * 0.5])
                        inner_d2 = np.array([target_dist_m * 0.5])

                    min_clearance_matrix[r_idx, d_idx, a_idx] = geom_min_clear

                    # Evaluate for each frequency in sweep
                    for f_hz in freq_list:
                        if geom_min_clear < 0.0:
                            # Geometrically blocked by intermediate terrain
                            crit_sub_idx = int(np.argmin(clearances))
                            crit_clearance = float(clearances[crit_sub_idx])
                            d1_c = float(inner_d1[crit_sub_idx])
                            d2_c = max(1.0, float(inner_d2[crit_sub_idx]))

                            v = RFPhysics.fresnel_kirchhoff_parameter(-crit_clearance, d1_c, d2_c, f_hz)
                            diff_loss = float(RFPhysics.knife_edge_diffraction_loss_db(v))
                            fspl = float(RFPhysics.free_space_path_loss_db(target_dist_m, f_hz))
                            f1_crit = float(RFPhysics.fresnel_radius(d1_c, d2_c, f_hz, n=1))
                            ratio = float(crit_clearance / max(1e-3, f1_crit))

                            results_by_freq[f_hz]["los_matrix"][r_idx, d_idx, a_idx] = False
                            results_by_freq[f_hz]["path_loss_db"][r_idx, d_idx, a_idx] = round(fspl + diff_loss, 1)
                            results_by_freq[f_hz]["clearance_ratio"][r_idx, d_idx, a_idx] = round(ratio, 2)
                        else:
                            f1_arr = RFPhysics.fresnel_radius(inner_d1, inner_d2, f_hz, n=1)
                            ratios = clearances / np.maximum(1e-3, f1_arr)
                            min_ratio = float(np.min(ratios))
                            crit_sub_idx = int(np.argmin(ratios))

                            crit_clearance = float(clearances[crit_sub_idx])
                            d1_c = float(inner_d1[crit_sub_idx])
                            d2_c = max(1.0, float(inner_d2[crit_sub_idx]))

                            v = RFPhysics.fresnel_kirchhoff_parameter(-crit_clearance, d1_c, d2_c, f_hz)
                            diff_loss = float(RFPhysics.knife_edge_diffraction_loss_db(v))
                            fspl = float(RFPhysics.free_space_path_loss_db(target_dist_m, f_hz))
                            total_loss = fspl + diff_loss

                            is_los = bool(min_ratio >= 0.60 and geom_min_clear >= 0.0)
                            results_by_freq[f_hz]["los_matrix"][r_idx, d_idx, a_idx] = is_los
                            results_by_freq[f_hz]["path_loss_db"][r_idx, d_idx, a_idx] = round(total_loss, 1)
                            results_by_freq[f_hz]["clearance_ratio"][r_idx, d_idx, a_idx] = round(min_ratio, 2)

        return {
            "metadata": {
                "tx_lat": self.tx_lat,
                "tx_lon": self.tx_lon,
                "tx_alt_amsl_m": self.tx_alt_amsl_m,
                "max_range_km": self.max_range_km,
                "min_alt_ft": self.min_alt_ft,
                "max_alt_ft": self.max_alt_ft,
                "alt_step_ft": self.alt_step_ft,
                "k_factor": self.k_factor,
            },
            "axes": {
                "altitudes_ft": [int(a) for a in self.altitude_levels_ft],
                "azimuths_deg": [round(float(b), 1) for b in self.azimuths_deg],
                "distances_km": [round(float(d), 1) for d in self.distances_km],
            },
            "frequencies_hz": freq_list,
            "min_clearance_matrix": min_clearance_matrix,
            "results_by_freq": results_by_freq
        }

    def _is_target_los(self, r_idx: int, target_dist_km: float, target_alt_m: float) -> bool:
        """Check if an aircraft/target at (target_dist_km, target_alt_m) has unobstructed line-of-sight."""
        target_d_m = target_dist_km * 1000.0
        dists_m, lats, lons, terrain_m, _ = self._get_or_compute_radial(r_idx)
        target_ground_m = float(np.interp(target_d_m, dists_m, terrain_m))
        if target_alt_m < target_ground_m:
            return False

        mask = dists_m <= target_d_m
        p_dists = dists_m[mask]
        p_terr = terrain_m[mask]
        if len(p_dists) > 0 and (target_d_m - p_dists[-1]) > 5.0:
            p_dists = np.append(p_dists, target_d_m)
            p_terr = np.append(p_terr, target_ground_m)
        if len(p_dists) < 2:
            return True

        bulge = RFPhysics.earth_bulge(p_dists, target_d_m - p_dists, k_factor=self.k_factor)
        eff_terr = p_terr + bulge
        min_tx_d = max(1.0, self.ignored_obstacle_radius_m)
        max_rx_d = max(min_tx_d + 10.0, target_d_m - 50.0)
        inner = (p_dists > min_tx_d) & (p_dists < max_rx_d)
        if not np.any(inner):
            return True

        ray = self.tx_alt_amsl_m + (p_dists / target_d_m) * (target_alt_m - self.tx_alt_amsl_m)
        clearances = ray[inner] - eff_terr[inner]
        return bool(np.all(clearances >= 0.0))

    def get_horizontal_slice(
        self,
        alt_ft: float,
        frequency_hz: float,
        cube_matrix_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract a 2D horizontal slice of coverage and path loss at a specified 1,000-ft altitude."""
        if cube_matrix_data is None:
            cube_matrix_data = self.compute_coverage_cube_matrix(frequency_hz)

        # Locate closest altitude index
        alts = np.array(cube_matrix_data["axes"]["altitudes_ft"])
        closest_a_idx = int(np.argmin(np.abs(alts - alt_ft)))
        actual_alt_ft = int(alts[closest_a_idx])

        freq_data = cube_matrix_data["results_by_freq"].get(frequency_hz)
        if not freq_data:
            # Pick first available frequency
            first_f = list(cube_matrix_data["results_by_freq"].keys())[0]
            freq_data = cube_matrix_data["results_by_freq"][first_f]

        los_slice = freq_data["los_matrix"][:, :, closest_a_idx]
        loss_slice = freq_data["path_loss_db"][:, :, closest_a_idx]

        # Generate GeoJSON contours / points for map visualization
        max_los_by_azimuth = []
        target_alt_m = actual_alt_ft * FT_TO_METERS

        for r_idx, azimuth in enumerate(self.azimuths_deg):
            radial_los = los_slice[r_idx, :]
            true_indices = np.where(radial_los)[0]

            if len(true_indices) == 0:
                # Target has zero line-of-sight along this entire radial at this altitude
                cont_dist_km = 0.0
            elif true_indices[-1] == len(self.distances_km) - 1:
                # Clear line-of-sight extends all the way to maximum outer range
                cont_dist_km = float(self.max_range_km)
            else:
                # Sub-grid precision search: coverage terminates between last clear and first blocked sample
                last_idx = int(true_indices[-1])
                d_lo = float(self.distances_km[last_idx])
                d_hi = float(self.distances_km[last_idx + 1])
                for _ in range(6):
                    d_mid = 0.5 * (d_lo + d_hi)
                    if self._is_target_los(r_idx, d_mid, target_alt_m):
                        d_lo = d_mid
                    else:
                        d_hi = d_mid
                cont_dist_km = round(float(d_lo), 2)

            if cont_dist_km > 0.0:
                dest_lat, dest_lon = GeoUtils.destination_point(
                    self.tx_lat, self.tx_lon, azimuth, cont_dist_km * 1000.0
                )
            else:
                dest_lat, dest_lon = self.tx_lat, self.tx_lon

            max_los_by_azimuth.append({
                "bearing_deg": round(float(azimuth), 1),
                "distance_km": round(cont_dist_km, 2),
                "lat": round(dest_lat, 5),
                "lon": round(dest_lon, 5)
            })

        # Build closed coverage boundary polygon in GeoJSON
        # Crucial: ALWAYS keep every point, including [tx_lon, tx_lat] for blocked radials (distance 0),
        # so blocked sectors indent cleanly to the transmitter instead of bridging across mountains!
        poly_coords = [[p["lon"], p["lat"]] for p in max_los_by_azimuth]
        if poly_coords and len(poly_coords) >= 3:
            poly_coords.append(poly_coords[0])  # close ring

        coverage_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [poly_coords]
                    } if len(poly_coords) >= 4 else {
                        "type": "Point",
                        "coordinates": [self.tx_lon, self.tx_lat]
                    },
                    "properties": {
                        "alt_ft": actual_alt_ft,
                        "frequency_hz": frequency_hz,
                        "max_range_km": float(np.max([p["distance_km"] for p in max_los_by_azimuth])) if max_los_by_azimuth else 0.0,
                        "avg_range_km": float(np.mean([p["distance_km"] for p in max_los_by_azimuth])) if max_los_by_azimuth else 0.0,
                    }
                }
            ]
        }

        # Calculate coverage percentage of circular disk at this altitude
        total_cells = self.n_radials * self.n_ranges
        covered_cells = int(np.sum(los_slice))
        coverage_pct = round((covered_cells / total_cells) * 100.0, 1)

        return {
            "alt_ft": actual_alt_ft,
            "alt_amsl_m": round(actual_alt_ft * FT_TO_METERS, 1),
            "frequency_hz": frequency_hz,
            "coverage_pct": coverage_pct,
            "boundary_points": max_los_by_azimuth,
            "geojson": coverage_geojson,
            "matrix": {
                "los": los_slice.tolist(),
                "path_loss_db": loss_slice.tolist()
            }
        }

    def get_vertical_slice(
        self,
        bearing_deg: float,
        frequency_hz: float
    ) -> Dict[str, Any]:
        """Extract a 2D vertical cross-section along a specific azimuth bearing across all 1,000-ft cubes."""
        # Find closest radial index
        bearing_norm = (bearing_deg + 360.0) % 360.0
        diffs = np.abs(self.azimuths_deg - bearing_norm)
        diffs = np.minimum(diffs, 360.0 - diffs)
        r_idx = int(np.argmin(diffs))
        actual_bearing = float(self.azimuths_deg[r_idx])

        dists_m, lats, lons, terrain_m, bulge_m = self._get_or_compute_radial(r_idx)

        # 2D grid along this radial: (distances_km x altitudes_ft)
        voxels_2d = []
        for d_idx, dist_km in enumerate(self.distances_km):
            target_dist_m = dist_km * 1000.0
            target_ground_m = float(np.interp(target_dist_m, dists_m, terrain_m))

            prof_mask = (dists_m <= target_dist_m)
            p_dists = dists_m[prof_mask]
            p_terr = terrain_m[prof_mask]

            if len(p_dists) > 0 and (target_dist_m - p_dists[-1]) > 5.0:
                p_dists = np.append(p_dists, target_dist_m)
                p_terr = np.append(p_terr, target_ground_m)

            if len(p_dists) < 2:
                continue

            bulge = RFPhysics.earth_bulge(p_dists, target_dist_m - p_dists, k_factor=self.k_factor)
            eff_terr = p_terr + bulge

            min_tx_d = max(1.0, self.ignored_obstacle_radius_m)
            max_rx_d = max(min_tx_d + 10.0, target_dist_m - 50.0)
            inner_idx = (p_dists > min_tx_d) & (p_dists < max_rx_d)

            for a_idx, alt_ft in enumerate(self.altitude_levels_ft):
                alt_m = alt_ft * FT_TO_METERS
                rx_above_ground = bool(alt_m > target_ground_m)

                if not rx_above_ground:
                    voxels_2d.append({
                        "distance_km": round(dist_km, 1),
                        "alt_ft": int(alt_ft),
                        "alt_amsl_m": round(alt_m, 1),
                        "min_clearance_m": round(alt_m - target_ground_m, 1),
                        "clearance_ratio": -99.0,
                        "is_los": False,
                        "optical_los": False,
                        "total_loss_db": 250.0
                    })
                    continue

                t_frac = p_dists / target_dist_m
                ray_m = self.tx_alt_amsl_m + t_frac * (alt_m - self.tx_alt_amsl_m)

                if np.any(inner_idx):
                    clearances = ray_m[inner_idx] - eff_terr[inner_idx]
                    geom_min_clear = float(np.min(clearances))
                    inner_d1 = p_dists[inner_idx]
                    inner_d2 = target_dist_m - inner_d1
                else:
                    clearances = np.array([alt_m - target_ground_m])
                    geom_min_clear = float(alt_m - target_ground_m)
                    inner_d1 = np.array([target_dist_m * 0.5])
                    inner_d2 = np.array([target_dist_m * 0.5])

                if geom_min_clear < 0.0:
                    crit_sub_idx = int(np.argmin(clearances))
                    crit_clearance = float(clearances[crit_sub_idx])
                    d1_c = float(inner_d1[crit_sub_idx])
                    d2_c = max(1.0, float(inner_d2[crit_sub_idx]))

                    v = RFPhysics.fresnel_kirchhoff_parameter(-crit_clearance, d1_c, d2_c, frequency_hz)
                    diff_loss = float(RFPhysics.knife_edge_diffraction_loss_db(v))
                    fspl = float(RFPhysics.free_space_path_loss_db(target_dist_m, frequency_hz))
                    f1_crit = float(RFPhysics.fresnel_radius(d1_c, d2_c, frequency_hz, n=1))
                    ratio = float(crit_clearance / max(1e-3, f1_crit))

                    voxels_2d.append({
                        "distance_km": round(dist_km, 1),
                        "alt_ft": int(alt_ft),
                        "alt_amsl_m": round(alt_m, 1),
                        "min_clearance_m": round(crit_clearance, 1),
                        "clearance_ratio": round(ratio, 2),
                        "is_los": False,
                        "optical_los": False,
                        "total_loss_db": round(fspl + diff_loss, 1)
                    })
                else:
                    f1_arr = RFPhysics.fresnel_radius(inner_d1, inner_d2, frequency_hz, 1)
                    ratios = clearances / np.maximum(1e-3, f1_arr)
                    min_ratio = float(np.min(ratios))
                    crit_sub_idx = int(np.argmin(ratios))

                    crit_clearance = float(clearances[crit_sub_idx])
                    d1_c = float(inner_d1[crit_sub_idx])
                    d2_c = max(1.0, float(inner_d2[crit_sub_idx]))

                    v = RFPhysics.fresnel_kirchhoff_parameter(-crit_clearance, d1_c, d2_c, frequency_hz)
                    diff_loss = float(RFPhysics.knife_edge_diffraction_loss_db(v))
                    fspl = float(RFPhysics.free_space_path_loss_db(target_dist_m, frequency_hz))
                    total_loss = fspl + diff_loss

                    voxels_2d.append({
                        "distance_km": round(dist_km, 1),
                        "alt_ft": int(alt_ft),
                        "alt_amsl_m": round(alt_m, 1),
                        "min_clearance_m": round(crit_clearance, 1),
                        "clearance_ratio": round(min_ratio, 2),
                        "is_los": bool(min_ratio >= 0.60 and geom_min_clear >= 0.0),
                        "optical_los": bool(geom_min_clear >= 0.0),
                        "total_loss_db": round(total_loss, 1)
                    })

        return {
            "bearing_deg": actual_bearing,
            "frequency_hz": frequency_hz,
            "max_range_km": self.max_range_km,
            "terrain_profile": {
                "distances_km": [round(d / 1000.0, 2) for d in dists_m],
                "terrain_elev_m": [round(float(h), 1) for h in terrain_m],
                "earth_bulge_m": [round(float(b), 1) for b in bulge_m],
                "effective_terrain_m": [round(float(t + b), 1) for t, b in zip(terrain_m, bulge_m)]
            },
            "voxels": voxels_2d
        }

    def get_3d_point_cloud(
        self,
        frequency_hz: float,
        cube_matrix_data: Optional[Dict[str, Any]] = None,
        subsample_step: int = 1
    ) -> List[Dict[str, Any]]:
        """Extract a lightweight 3D point cloud of 1,000-ft cubes for WebGL / Three.js 3D rendering.
        
        Returns points in local 3D Cartesian coordinates (X = East km, Y = North km, Z = Alt km).
        """
        if cube_matrix_data is None:
            cube_matrix_data = self.compute_coverage_cube_matrix(frequency_hz)

        freq_data = cube_matrix_data["results_by_freq"].get(frequency_hz)
        if not freq_data:
            first_f = list(cube_matrix_data["results_by_freq"].keys())[0]
            freq_data = cube_matrix_data["results_by_freq"][first_f]

        los_mat = freq_data["los_matrix"]
        loss_mat = freq_data["path_loss_db"]

        points_3d = []
        for r_idx in range(0, self.n_radials, subsample_step):
            az_rad = math.radians(float(self.azimuths_deg[r_idx]))
            sin_az = math.sin(az_rad)
            cos_az = math.cos(az_rad)

            for d_idx in range(0, self.n_ranges, subsample_step):
                dist_km = float(self.distances_km[d_idx])
                # Local East-North coordinates (km)
                x_km = dist_km * sin_az
                y_km = dist_km * cos_az

                for a_idx in range(0, self.n_alts, subsample_step):
                    alt_ft = float(self.altitude_levels_ft[a_idx])
                    alt_km = (alt_ft * FT_TO_METERS) / 1000.0

                    is_los = bool(los_mat[r_idx, d_idx, a_idx])
                    loss_db = float(loss_mat[r_idx, d_idx, a_idx])

                    points_3d.append({
                        "x": round(x_km, 2),
                        "y": round(y_km, 2),
                        "z": round(alt_km, 2),
                        "alt_ft": int(alt_ft),
                        "dist_km": round(dist_km, 1),
                        "bearing_deg": round(float(self.azimuths_deg[r_idx]), 1),
                        "is_los": is_los,
                        "path_loss_db": round(loss_db, 1)
                    })

        return points_3d
