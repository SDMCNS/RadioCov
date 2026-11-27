"""Unit tests for RadioCov engine, volumetric 1,000-ft cubes, and slicing operations."""

import unittest
import numpy as np
from radiocov.core.terrain import TerrainProvider
from radiocov.core.engine import RFCoverageEngine
from radiocov.core.voxels import VolumetricCoverageGrid


class TestEngineAndVoxels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terrain = TerrainProvider()
        cls.engine = RFCoverageEngine(terrain_provider=cls.terrain)

    def test_point_to_point_clear_path(self):
        # High altitude receiver above mountain transmitter
        res = self.engine.evaluate_point_to_point(
            tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,  # Zugspitze
            rx_lat=47.8, rx_lon=11.2, rx_alt_amsl_m=10000.0,
            frequencies_hz=[100.0e6, 1000.0e6]
        )
        self.assertTrue(res["optical_los"])
        self.assertTrue(res["radio_los"])
        self.assertGreater(res["min_clearance_m"], 0.0)
        self.assertIn(100.0e6, res["frequencies"])
        self.assertIn(1000.0e6, res["frequencies"])
        self.assertEqual(res["frequencies"][100.0e6]["diffraction_loss_db"], 0.0)

    def test_radial_profile(self):
        res = self.engine.evaluate_radial_profile(
            tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,
            bearing_deg=45.0,
            max_distance_km=50.0,
            target_alt_amsl_m=3000.0,
            frequency_hz=1000.0e6
        )
        self.assertEqual(res["bearing_deg"], 45.0)
        self.assertAlmostEqual(res["distance_km"], 50.0, delta=1.0)
        self.assertIsNotNone(res["profile"])
        self.assertGreater(len(res["profile"]["distances_km"]), 10)

    def test_radial_profile_blockage_distance(self):
        # Target behind Alpine terrain at low altitude (700m AMSL)
        res = self.engine.evaluate_radial_profile(
            tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,
            bearing_deg=180.0,  # South into high Austrian Alps
            max_distance_km=40.0,
            target_alt_amsl_m=800.0,  # Low target
            frequency_hz=1000.0e6
        )
        # Should detect blockage and provide exact blockage distance
        self.assertFalse(res["optical_los"])
        self.assertIsNotNone(res["blockage"])
        self.assertIn("distance_km", res["blockage"])
        self.assertGreater(res["blockage"]["distance_km"], 0.0)
        self.assertLessEqual(res["blockage"]["distance_km"], 40.0)
        self.assertIn("penetration_m", res["blockage"])

    def test_volumetric_grid_1000ft_cubes(self):
        # 1,000-ft cubes from 2,000 to 10,000 ft AMSL
        grid = VolumetricCoverageGrid(
            engine=self.engine,
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_m=2962.0,
            max_range_km=30.0,
            min_alt_ft=2000.0,
            max_alt_ft=10000.0,
            alt_step_ft=1000.0,
            num_radials=12,
            range_step_km=5.0
        )
        self.assertEqual(grid.alt_step_ft, 1000.0)
        self.assertEqual(grid.n_alts, 9)  # 2k, 3k, 4k, 5k, 6k, 7k, 8k, 9k, 10k

        matrix_data = grid.compute_coverage_cube_matrix([500.0e6, 1500.0e6])
        self.assertIn("min_clearance_matrix", matrix_data)
        self.assertIn(500.0e6, matrix_data["results_by_freq"])
        self.assertIn(1500.0e6, matrix_data["results_by_freq"])

        # Test Horizontal Slice
        h_slice = grid.get_horizontal_slice(5000.0, 500.0e6, cube_matrix_data=matrix_data)
        self.assertEqual(h_slice["alt_ft"], 5000)
        self.assertIn("geojson", h_slice)
        self.assertGreaterEqual(h_slice["coverage_pct"], 0.0)
        self.assertLessEqual(h_slice["coverage_pct"], 100.0)

        # Test Vertical Slice
        v_slice = grid.get_vertical_slice(90.0, 500.0e6)
        self.assertIn("terrain_profile", v_slice)
        self.assertIn("voxels", v_slice)
        self.assertGreater(len(v_slice["voxels"]), 0)

        # Test 3D Point Cloud
        points_3d = grid.get_3d_point_cloud(500.0e6, cube_matrix_data=matrix_data)
        self.assertGreater(len(points_3d), 0)
        p0 = points_3d[0]
        self.assertIn("x", p0)
        self.assertIn("y", p0)
        self.assertIn("z", p0)
        self.assertIn("is_los", p0)

    def test_first_physical_blockage_precedence_over_underground_rx(self):
        """Verify that intermediate mountain ridge intersection takes precedence over underground receiver at max range.
        
        Test case from user scenario:
        Tx: Zugspitze (2992m AMSL), Bearing 95°, Max Range: 40km, Target Alt: 7,000 ft (2133.6m AMSL), Freq: 10 GHz.
        The ray intersects an Alpine ridge at ~29.8 km, while at 40 km the local terrain is also > 2133.6m.
        The engine must report the first terrain intersection (~29.8 km), NOT 40.0 km.
        """
        res = self.engine.evaluate_radial_profile(
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_m=2992.0,
            bearing_deg=95.0,
            max_distance_km=40.0,
            target_alt_amsl_m=7000.0 * 0.3048,
            frequency_hz=10000.0e6
        )
        self.assertFalse(res["optical_los"])
        self.assertFalse(res["radio_los"])
        self.assertIsNotNone(res["blockage"])
        # Must report the intermediate terrain intersection, not receiver terminal distance 40.0 km
        self.assertEqual(res["blockage"]["type"], "terrain_intersection")
        self.assertLess(res["blockage"]["distance_km"], 35.0)
        self.assertGreater(res["blockage"]["distance_km"], 25.0)
        self.assertGreater(res["blockage"]["penetration_m"], 0.0)

    def test_voxel_and_radial_profile_consistency_zugspitze(self):
        """Verify consistency between 3D volumetric grid and point-to-point radial profile."""
        grid = VolumetricCoverageGrid(
            engine=self.engine,
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_m=2992.0,
            max_range_km=40.0,
            min_alt_ft=7000.0,
            max_alt_ft=7000.0,
            alt_step_ft=1000.0,
            num_radials=36,
            range_step_km=2.0
        )
        freq = 10000.0e6
        matrix_data = grid.compute_coverage_cube_matrix(freq)
        los_matrix = matrix_data["results_by_freq"][freq]["los_matrix"][:, :, 0]

        # For bearing 250° and 90°, verify that voxels match radial profile evaluations
        for b_test in [90.0, 180.0, 250.0]:
            r_idx = int(np.argmin(np.abs(grid.azimuths_deg - b_test)))
            for d_idx, dist_km in enumerate(grid.distances_km):
                voxel_los = los_matrix[r_idx, d_idx]
                pt = self.engine.evaluate_radial_profile(
                    tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2992.0,
                    bearing_deg=grid.azimuths_deg[r_idx],
                    max_distance_km=dist_km,
                    target_alt_amsl_m=7000.0 * 0.3048,
                    frequency_hz=freq,
                    num_profile_points=250
                )
                pt_los = bool(pt["optical_los"] and pt["radio_los"])
                # If the point-to-point path is physically blocked by an obstacle, voxel must not claim clear LoS
                if not pt["optical_los"]:
                    self.assertFalse(
                        voxel_los,
                        f"Voxel claims LoS at bearing {grid.azimuths_deg[r_idx]}° distance {dist_km} km, "
                        f"but engine profile proves optical blockage: {pt.get('blockage')}"
                    )

    def test_ignored_obstacle_compound_radius(self):
        """Verify that setting ignored_obstacle_radius_m (25-100m) properly masks near-field compound obstacles."""
        res_75m = self.engine.evaluate_radial_profile(
            tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2992.0,
            bearing_deg=90.0,
            max_distance_km=40.0,
            target_alt_amsl_m=10000.0 * 0.3048,
            frequency_hz=1000.0e6,
            ignored_obstacle_radius_m=75.0
        )
        self.assertEqual(res_75m["ignored_obstacle_radius_m"], 75.0)

        # Volumetric grid with compound radius
        grid = VolumetricCoverageGrid(
            engine=self.engine,
            tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2992.0,
            max_range_km=20.0,
            min_alt_ft=5000.0, max_alt_ft=10000.0, alt_step_ft=5000.0,
            num_radials=12, range_step_km=5.0,
            ignored_obstacle_radius_m=100.0
        )
        self.assertEqual(grid.ignored_obstacle_radius_m, 100.0)
        v_slice = grid.get_vertical_slice(90.0, 1000.0e6)
        self.assertGreater(len(v_slice["voxels"]), 0)

    def test_southerly_coverage_at_8000ft_and_feet_units(self):
        """Verify that at 8,000 ft AMSL from Zugspitze (9,718 ft):
        1. Radial 225° reaches ~60 km before hitting Alps terrain.
        2. Horizontal slice boundary along 225° extends to ~60 km, NOT collapsing to 0 km.
        3. All altitude fields and profiles support feet.
        """
        # 1. Radial profile at 225° with altitude in feet
        res = self.engine.evaluate_radial_profile(
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_ft=9718.0,
            bearing_deg=225.0,
            max_distance_km=100.0,
            target_alt_amsl_ft=8000.0,
            frequency_hz=1090.0e6,
            num_profile_points=250,
            ignored_obstacle_radius_m=100.0
        )
        self.assertIn("terrain_elev_ft", res["profile"])
        self.assertIn("los_ray_ft", res["profile"])
        self.assertIsNotNone(res["blockage"])
        blk_dist = res["blockage"]["distance_km"]
        # Must reach ~60.08 km
        self.assertGreater(blk_dist, 58.0)
        self.assertLess(blk_dist, 62.0)
        self.assertIn("terrain_elevation_ft", res["blockage"])

        # 2. Horizontal slice at 8,000 ft
        grid = VolumetricCoverageGrid(
            engine=self.engine,
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_ft=9718.0,
            max_range_km=100.0,
            min_alt_ft=8000.0,
            max_alt_ft=8000.0,
            num_radials=72,
            range_step_km=2.5,
            ignored_obstacle_radius_m=100.0
        )
        slice_data = grid.get_horizontal_slice(alt_ft=8000.0, frequency_hz=1090.0e6)
        self.assertGreater(slice_data["coverage_pct"], 60.0)

        # Check radial 225° in boundary points
        pts_225 = [p for p in slice_data["boundary_points"] if abs(p["bearing_deg"] - 225.0) < 3.0]
        self.assertEqual(len(pts_225), 1)
        # Must be ~60 km, NOT 0.0 km
        self.assertGreater(pts_225[0]["distance_km"], 55.0)
        self.assertLess(pts_225[0]["distance_km"], 65.0)

    def test_horizontal_slice_consistency_with_vertical_profiles_1000_to_8000ft(self):
        """Verify that horizontal slice boundaries match vertical profile blockages for 1,000 to 8,000 ft AMSL:
        - At 1,000 ft: all southerly bearings (75° to 245°) have 0.0 km reach (airspace is below Alps ground).
        - At 3,000 ft: south bearings 150° to 245° have 0.0 km reach.
        - At 5,000 ft: south bearings 90°, 120°, 180°, 210° have 0.0 km reach.
        - At 7,000 ft: bearing 180° reach is ~6.3 km (blocked by Alpine peak).
        - At 8,000 ft: bearing 150° reach is ~25 km, bearing 225° is ~60 km.
        """
        grid = VolumetricCoverageGrid(
            engine=self.engine,
            tx_lat=47.4211,
            tx_lon=10.9853,
            tx_alt_amsl_ft=9718.0,
            max_range_km=100.0,
            min_alt_ft=1000.0,
            max_alt_ft=8000.0,
            alt_step_ft=1000.0,
            num_radials=72,
            range_step_km=2.5,
            ignored_obstacle_radius_m=100.0
        )
        matrix_data = grid.compute_coverage_cube_matrix(1090.0e6)

        # 1. At 1,000 ft AMSL
        slice_1k = grid.get_horizontal_slice(1000.0, 1090.0e6, cube_matrix_data=matrix_data)
        self.assertEqual(slice_1k["coverage_pct"], 0.0)
        for pt in slice_1k["boundary_points"]:
            if 75.0 <= pt["bearing_deg"] <= 245.0:
                self.assertEqual(pt["distance_km"], 0.0, f"Bearing {pt['bearing_deg']} at 1000ft should be 0.0km")

        # 2. At 3,000 ft AMSL
        slice_3k = grid.get_horizontal_slice(3000.0, 1090.0e6, cube_matrix_data=matrix_data)
        pts_3k = {p["bearing_deg"]: p["distance_km"] for p in slice_3k["boundary_points"]}
        for b in [90.0, 120.0, 150.0, 180.0, 210.0, 225.0]:
            closest_b = min(pts_3k.keys(), key=lambda x: abs(x - b))
            self.assertEqual(pts_3k[closest_b], 0.0, f"Bearing {b}° at 3000ft should be 0.0km")

        # 3. At 5,000 ft AMSL
        slice_5k = grid.get_horizontal_slice(5000.0, 1090.0e6, cube_matrix_data=matrix_data)
        pts_5k = {p["bearing_deg"]: p["distance_km"] for p in slice_5k["boundary_points"]}
        for b in [90.0, 120.0, 180.0, 210.0]:
            closest_b = min(pts_5k.keys(), key=lambda x: abs(x - b))
            self.assertEqual(pts_5k[closest_b], 0.0, f"Bearing {b}° at 5000ft should be 0.0km")

        # 4. At 7,000 ft AMSL
        slice_7k = grid.get_horizontal_slice(7000.0, 1090.0e6, cube_matrix_data=matrix_data)
        pts_7k = {p["bearing_deg"]: p["distance_km"] for p in slice_7k["boundary_points"]}
        b180 = min(pts_7k.keys(), key=lambda x: abs(x - 180.0))
        self.assertGreater(pts_7k[b180], 4.0)
        self.assertLess(pts_7k[b180], 10.0)

        # 5. At 8,000 ft AMSL
        slice_8k = grid.get_horizontal_slice(8000.0, 1090.0e6, cube_matrix_data=matrix_data)
        pts_8k = {p["bearing_deg"]: p["distance_km"] for p in slice_8k["boundary_points"]}
        b150 = min(pts_8k.keys(), key=lambda x: abs(x - 150.0))
        self.assertGreater(pts_8k[b150], 20.0)
        self.assertLess(pts_8k[b150], 30.0)
        b225 = min(pts_8k.keys(), key=lambda x: abs(x - 225.0))
        self.assertGreater(pts_8k[b225], 55.0)
        self.assertLess(pts_8k[b225], 65.0)


if __name__ == "__main__":
    unittest.main()
