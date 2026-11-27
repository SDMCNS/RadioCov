"""Pure Radio Frequency Coverage Assessment Engine.

Computes point-to-point and multi-radial line of sight, Earth curvature,
Fresnel zone clearance, and diffraction loss across arbitrary frequency spectra.
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from radiocov.config import (
    SPEED_OF_LIGHT,
    EARTH_MEAN_RADIUS,
    STANDARD_K_FACTOR,
    FT_TO_METERS,
    METERS_TO_FT,
)
from radiocov.core.physics import RFPhysics
from radiocov.core.geo import GeoUtils
from radiocov.core.terrain import TerrainProvider


class RFCoverageEngine:
    """Core computational engine for radio spectrum coverage and line-of-sight."""

    def __init__(
        self,
        terrain_provider: Optional[TerrainProvider] = None,
        k_factor: float = STANDARD_K_FACTOR
    ):
        self.terrain = terrain_provider or TerrainProvider()
        self.k_factor = k_factor

    def evaluate_point_to_point(
        self,
        tx_lat: float,
        tx_lon: float,
        tx_alt_amsl_m: Optional[float] = None,
        rx_lat: float = 0.0,
        rx_lon: float = 0.0,
        rx_alt_amsl_m: Optional[float] = None,
        frequencies_hz: Union[float, List[float]] = 1000.0e6,
        num_profile_points: int = 200,
        k_factor: Optional[float] = None,
        ignored_obstacle_radius_m: float = 50.0,
        tx_alt_amsl_ft: Optional[float] = None,
        rx_alt_amsl_ft: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Assess RF Line of Sight and propagation between a transmitter and receiver point.
        
        Args:
            tx_lat, tx_lon: Transmitter coordinates
            tx_alt_amsl_m / tx_alt_amsl_ft: Transmitter altitude AMSL (meters or feet)
            rx_lat, rx_lon: Receiver coordinates
            rx_alt_amsl_m / rx_alt_amsl_ft: Receiver altitude AMSL (meters or feet)
            frequencies_hz: Single frequency or list of frequencies in Hz
            num_profile_points: Number of terrain profile samples along the geodesic
            k_factor: Atmospheric refraction factor (default 4/3)
            ignored_obstacle_radius_m: Compound mask radius (25-100m)
            
        Returns:
            Dict containing detailed path profile, LoS status, clearance, and per-frequency metrics in both feet and meters.
        """
        # Resolve altitude inputs (prefer feet if given, else meters)
        if tx_alt_amsl_ft is not None:
            tx_alt_amsl_m = float(tx_alt_amsl_ft) * FT_TO_METERS
        elif tx_alt_amsl_m is None:
            tx_alt_amsl_m = 2962.0
            
        if rx_alt_amsl_ft is not None:
            rx_alt_amsl_m = float(rx_alt_amsl_ft) * FT_TO_METERS
        elif rx_alt_amsl_m is None:
            rx_alt_amsl_m = 1000.0

        k = k_factor if k_factor is not None else self.k_factor
        freq_list = [frequencies_hz] if isinstance(frequencies_hz, (int, float)) else list(frequencies_hz)

        # 1. Geodesic distance and bearing
        distance_m = GeoUtils.haversine_distance_m(tx_lat, tx_lon, rx_lat, rx_lon)
        bearing_deg = GeoUtils.initial_bearing_deg(tx_lat, tx_lon, rx_lat, rx_lon)

        if distance_m < 1.0:
            return {
                "distance_km": 0.0,
                "bearing_deg": bearing_deg,
                "optical_los": True,
                "radio_los": True,
                "min_clearance_m": rx_alt_amsl_m - tx_alt_amsl_m,
                "critical_obstacle": None,
                "frequencies": {
                    f: {"fspl_db": 0.0, "diffraction_loss_db": 0.0, "total_path_loss_db": 0.0, "fresnel_clearance_ratio": 1.0}
                    for f in freq_list
                },
                "profile": None
            }

        # 2. Extract terrain profile
        distances_m, lats, lons = GeoUtils.interpolate_radial_points(
            tx_lat, tx_lon, bearing_deg, distance_m, num_profile_points
        )
        elevs = self.terrain.get_elevations(list(zip(lats, lons)))
        terrain_m = np.array(elevs, dtype=np.float64)

        # 3. Direct line-of-sight ray altitude (linear interpolation from Tx to Rx)
        t_fractions = distances_m / distance_m
        los_ray_m = tx_alt_amsl_m + t_fractions * (rx_alt_amsl_m - tx_alt_amsl_m)

        # 4. Apparent Earth bulge under k-factor refraction
        d1_m = distances_m
        d2_m = distance_m - distances_m
        earth_bulge_m = RFPhysics.earth_bulge(d1_m, d2_m, k_factor=k)

        # 5. Effective obstacle height (terrain + earth curvature)
        effective_terrain_m = terrain_m + earth_bulge_m
        clearance_m = los_ray_m - effective_terrain_m

        # Verify receiver is above local ground elevation
        rx_ground_m = float(terrain_m[-1])
        rx_above_ground = bool(rx_alt_amsl_m >= rx_ground_m)

        # Mask end points (transmitter and receiver locations themselves)
        # Apply compound / DEM alignment tolerance radius around transmitter mast (25-100m)
        min_tx_d = max(1.0, float(ignored_obstacle_radius_m))
        max_rx_d = max(min_tx_d + 10.0, distance_m - 50.0)
        inner_mask = (distances_m > min_tx_d) & (distances_m < max_rx_d)
        if np.any(inner_mask):
            min_idx = np.argmin(clearance_m[inner_mask])
            actual_min_idx = np.where(inner_mask)[0][min_idx]
            min_geom_clearance = float(clearance_m[actual_min_idx])
            geom_crit_dist_m = float(distances_m[actual_min_idx])
            geom_crit_lat = float(lats[actual_min_idx])
            geom_crit_lon = float(lons[actual_min_idx])
            geom_crit_terrain_m = float(terrain_m[actual_min_idx])
            geom_crit_bulge_m = float(earth_bulge_m[actual_min_idx])
        else:
            actual_min_idx = 0
            min_geom_clearance = float(np.min(clearance_m))
            geom_crit_dist_m = float(distances_m[0])
            geom_crit_lat = float(lats[0])
            geom_crit_lon = float(lons[0])
            geom_crit_terrain_m = float(terrain_m[0])
            geom_crit_bulge_m = 0.0

        optical_los = bool(min_geom_clearance >= 0.0 and rx_above_ground)

        # 6. Per-frequency analysis: identify critical obstacle by minimizing Fresnel clearance ratio (C / F1)
        freq_results = {}
        primary_crit_info = None

        for f_idx, f_hz in enumerate(freq_list):
            if np.any(inner_mask) and rx_above_ground:
                # Vectorized Fresnel radius along inner path
                f1_arr = RFPhysics.fresnel_radius(distances_m[inner_mask], distance_m - distances_m[inner_mask], f_hz, n=1)
                ratio_arr = clearance_m[inner_mask] / np.maximum(1e-3, f1_arr)
                
                crit_sub_idx = np.argmin(ratio_arr)
                crit_idx = np.where(inner_mask)[0][crit_sub_idx]
                
                d1_crit = float(distances_m[crit_idx])
                d2_crit = max(1.0, distance_m - d1_crit)
                f1_crit_radius = float(f1_arr[crit_sub_idx])
                clearance_ratio = float(ratio_arr[crit_sub_idx])
                crit_clearance = float(clearance_m[crit_idx])
                obs_height = -crit_clearance
                c_lat = float(lats[crit_idx])
                c_lon = float(lons[crit_idx])
                c_terr = float(terrain_m[crit_idx])
                c_bulge = float(earth_bulge_m[crit_idx])
            else:
                d1_crit = distance_m * 0.5
                d2_crit = distance_m * 0.5
                f1_crit_radius = float(RFPhysics.fresnel_radius(d1_crit, d2_crit, f_hz, n=1))
                crit_clearance = rx_alt_amsl_m - rx_ground_m if not rx_above_ground else min_geom_clearance
                clearance_ratio = float(crit_clearance / max(1.0, f1_crit_radius))
                obs_height = -crit_clearance
                c_lat = rx_lat
                c_lon = rx_lon
                c_terr = rx_ground_m
                c_bulge = 0.0

            # Dimensionless diffraction parameter v
            v = RFPhysics.fresnel_kirchhoff_parameter(obs_height, d1_crit, d2_crit, f_hz)
            diff_loss = float(RFPhysics.knife_edge_diffraction_loss_db(v))
            fspl = float(RFPhysics.free_space_path_loss_db(distance_m, f_hz))
            total_loss = fspl + diff_loss

            freq_results[f_hz] = {
                "wavelength_m": round(SPEED_OF_LIGHT / f_hz, 4),
                "fresnel_1_radius_m": round(f1_crit_radius, 2),
                "fresnel_clearance_ratio": round(clearance_ratio, 3),
                "fresnel_cleared_60pct": bool(clearance_ratio >= 0.60 and rx_above_ground),
                "diffraction_v": round(v, 3),
                "diffraction_loss_db": round(diff_loss, 2),
                "fspl_db": round(fspl, 2),
                "total_path_loss_db": round(total_loss, 2)
            }

            if f_idx == 0:
                primary_crit_info = {
                    "distance_km": round(d1_crit / 1000.0, 3),
                    "lat": round(c_lat, 5),
                    "lon": round(c_lon, 5),
                    "terrain_elevation_m": round(c_terr, 1),
                    "earth_bulge_m": round(c_bulge, 1),
                    "clearance_m": round(crit_clearance, 2),
                    "fresnel_radius_m": round(f1_crit_radius, 2),
                    "clearance_ratio": round(clearance_ratio, 3)
                }

        # Select primary frequency (first in list) for summary booleans
        primary_f = freq_list[0]
        radio_los = bool(freq_results[primary_f]["fresnel_cleared_60pct"])

        # Detect and calculate exact blockage location
        blockage_info = None
        blocked_mask = inner_mask & (clearance_m < 0.0)

        # 1. Intermediate terrain blockage takes absolute physical precedence:
        # If the ray strikes a mountain peak or ridge along the path, this is the first point of blockage
        if np.any(blocked_mask):
            first_blk_idx = int(np.where(blocked_mask)[0][0])
            # High-precision linear interpolation for sub-meter intersection distance
            if first_blk_idx > 0 and clearance_m[first_blk_idx - 1] > 0:
                c1 = float(clearance_m[first_blk_idx - 1])
                c2 = float(clearance_m[first_blk_idx])
                d1 = float(distances_m[first_blk_idx - 1])
                d2 = float(distances_m[first_blk_idx])
                exact_d = d1 + (0.0 - c1) / (c2 - c1) * (d2 - d1)
            else:
                exact_d = float(distances_m[first_blk_idx])

            blockage_info = {
                "distance_km": round(exact_d / 1000.0, 3),
                "peak_distance_km": round(geom_crit_dist_m / 1000.0, 3),
                "lat": round(geom_crit_lat, 5),
                "lon": round(geom_crit_lon, 5),
                "terrain_elevation_ft": round(geom_crit_terrain_m * METERS_TO_FT, 1),
                "terrain_elevation_m": round(geom_crit_terrain_m, 1),
                "earth_bulge_ft": round(geom_crit_bulge_m * METERS_TO_FT, 1),
                "earth_bulge_m": round(geom_crit_bulge_m, 1),
                "penetration_ft": round(-min_geom_clearance * METERS_TO_FT, 1),
                "penetration_m": round(-min_geom_clearance, 1),
                "clearance_ft": round(min_geom_clearance * METERS_TO_FT, 1),
                "clearance_m": round(min_geom_clearance, 1),
                "type": "terrain_intersection",
                "description": f"LOS ray blocked by terrain at {exact_d / 1000.0:.2f} km (Peak obstacle at {geom_crit_dist_m / 1000.0:.2f} km with {geom_crit_terrain_m * METERS_TO_FT:.0f} ft AMSL / {geom_crit_terrain_m:.0f} m AMSL)"
            }
        # 2. Only if the ray was clear up to destination, but the target receiver itself is underground:
        elif not rx_above_ground:
            blockage_info = {
                "distance_km": round(distance_m / 1000.0, 3),
                "peak_distance_km": round(distance_m / 1000.0, 3),
                "lat": round(rx_lat, 5),
                "lon": round(rx_lon, 5),
                "type": "underground_rx",
                "terrain_elevation_ft": round(rx_ground_m * METERS_TO_FT, 1),
                "terrain_elevation_m": round(rx_ground_m, 1),
                "earth_bulge_ft": round(float(earth_bulge_m[-1]) * METERS_TO_FT, 1),
                "earth_bulge_m": round(float(earth_bulge_m[-1]), 1),
                "penetration_ft": round((rx_ground_m - rx_alt_amsl_m) * METERS_TO_FT, 1),
                "penetration_m": round(rx_ground_m - rx_alt_amsl_m, 1),
                "clearance_ft": round((rx_alt_amsl_m - rx_ground_m) * METERS_TO_FT, 1),
                "clearance_m": round(rx_alt_amsl_m - rx_ground_m, 1),
                "description": f"Receiver target is underground (Terrain: {rx_ground_m * METERS_TO_FT:.0f} ft AMSL, Rx: {rx_alt_amsl_m * METERS_TO_FT:.0f} ft AMSL)"
            }
        # 3. Fresnel zone obstruction (optical LOS clear, but 1st Fresnel zone encroached > 40%)
        elif not radio_los and primary_crit_info:
            blockage_info = {
                "distance_km": primary_crit_info["distance_km"],
                "peak_distance_km": primary_crit_info["distance_km"],
                "lat": primary_crit_info["lat"],
                "lon": primary_crit_info["lon"],
                "terrain_elevation_ft": round(primary_crit_info["terrain_elevation_m"] * METERS_TO_FT, 1),
                "terrain_elevation_m": primary_crit_info["terrain_elevation_m"],
                "earth_bulge_ft": round(primary_crit_info["earth_bulge_m"] * METERS_TO_FT, 1),
                "earth_bulge_m": primary_crit_info["earth_bulge_m"],
                "clearance_ft": round(primary_crit_info["clearance_m"] * METERS_TO_FT, 1),
                "clearance_m": primary_crit_info["clearance_m"],
                "fresnel_radius_ft": round(primary_crit_info["fresnel_radius_m"] * METERS_TO_FT, 1),
                "fresnel_radius_m": primary_crit_info["fresnel_radius_m"],
                "clearance_ratio": primary_crit_info["clearance_ratio"],
                "type": "fresnel_encroachment",
                "description": f"1st Fresnel zone obstruction at {primary_crit_info['distance_km']:.2f} km (Clearance ratio: {primary_crit_info['clearance_ratio']:.2f} < 0.60)"
            }

        return {
            "tx": {
                "lat": tx_lat,
                "lon": tx_lon,
                "alt_amsl_ft": round(tx_alt_amsl_m * METERS_TO_FT, 1),
                "alt_amsl_m": round(tx_alt_amsl_m, 1)
            },
            "rx": {
                "lat": rx_lat,
                "lon": rx_lon,
                "alt_amsl_ft": round(rx_alt_amsl_m * METERS_TO_FT, 1),
                "alt_amsl_m": round(rx_alt_amsl_m, 1)
            },
            "distance_km": round(distance_m / 1000.0, 3),
            "bearing_deg": round(bearing_deg, 2),
            "optical_los": optical_los,
            "radio_los": radio_los,
            "min_clearance_ft": round((primary_crit_info["clearance_m"] if primary_crit_info else min_geom_clearance) * METERS_TO_FT, 1),
            "min_clearance_m": primary_crit_info["clearance_m"] if primary_crit_info else round(min_geom_clearance, 2),
            "critical_obstacle": primary_crit_info,
            "blockage": blockage_info,
            "ignored_obstacle_radius_m": min_tx_d,
            "frequencies": freq_results,
            "profile": {
                "distances_km": [round(d / 1000.0, 3) for d in distances_m],
                "terrain_elev_ft": [round(float(h) * METERS_TO_FT, 1) for h in terrain_m],
                "terrain_elev_m": [round(float(h), 1) for h in terrain_m],
                "earth_bulge_ft": [round(float(b) * METERS_TO_FT, 1) for b in earth_bulge_m],
                "earth_bulge_m": [round(float(b), 1) for b in earth_bulge_m],
                "effective_terrain_ft": [round(float(e) * METERS_TO_FT, 1) for e in effective_terrain_m],
                "effective_terrain_m": [round(float(e), 1) for e in effective_terrain_m],
                "los_ray_ft": [round(float(r) * METERS_TO_FT, 1) for r in los_ray_m],
                "los_ray_m": [round(float(r), 1) for r in los_ray_m],
                "fresnel_bottom_ft": [
                    round(float(los_ray_m[i] - RFPhysics.fresnel_radius(distances_m[i], distance_m - distances_m[i], primary_f, 1)) * METERS_TO_FT, 1)
                    for i in range(len(distances_m))
                ],
                "fresnel_bottom_m": [
                    round(float(los_ray_m[i] - RFPhysics.fresnel_radius(distances_m[i], distance_m - distances_m[i], primary_f, 1)), 1)
                    for i in range(len(distances_m))
                ]
            }
        }

    def evaluate_radial_profile(
        self,
        tx_lat: float,
        tx_lon: float,
        tx_alt_amsl_m: Optional[float] = None,
        bearing_deg: float = 0.0,
        max_distance_km: float = 100.0,
        target_alt_amsl_m: Optional[float] = None,
        frequency_hz: float = 1000.0e6,
        num_profile_points: int = 250,
        k_factor: Optional[float] = None,
        ignored_obstacle_radius_m: float = 50.0,
        tx_alt_amsl_ft: Optional[float] = None,
        target_alt_amsl_ft: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate a complete 2D vertical cross-section along an azimuth radial."""
        max_dist_m = max_distance_km * 1000.0
        dest_lat, dest_lon = GeoUtils.destination_point(tx_lat, tx_lon, bearing_deg, max_dist_m)
        return self.evaluate_point_to_point(
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            tx_alt_amsl_m=tx_alt_amsl_m,
            rx_lat=dest_lat,
            rx_lon=dest_lon,
            rx_alt_amsl_m=target_alt_amsl_m,
            frequencies_hz=frequency_hz,
            num_profile_points=num_profile_points,
            k_factor=k_factor,
            ignored_obstacle_radius_m=ignored_obstacle_radius_m,
            tx_alt_amsl_ft=tx_alt_amsl_ft,
            rx_alt_amsl_ft=target_alt_amsl_ft
        )
