"""Unit tests for RadioCov FastAPI endpoints."""

import unittest
from fastapi.testclient import TestClient

from radiocov.api.server import app


class TestRadioCovAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_presets_endpoint(self):
        resp = self.client.get("/api/presets")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("spectrum_bands", data)
        self.assertIn("sample_locations", data)
        self.assertIn("VHF_AIR_MARINE", data["spectrum_bands"])

    def test_evaluate_point_endpoint(self):
        payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "rx_lat": 47.7,
            "rx_lon": 11.2,
            "rx_alt_amsl_m": 8000.0,
            "frequencies_hz": [1000.0e6, 2000.0e6],
            "k_factor": 1.333
        }
        resp = self.client.post("/api/evaluate-point", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("optical_los", data)
        self.assertIn("frequencies", data)
        self.assertIn("1000000000.0", data["frequencies"])

    def test_radial_profile_endpoint(self):
        payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "bearing_deg": 90.0,
            "max_distance_km": 40.0,
            "target_alt_amsl_m": 4000.0,
            "frequency_hz": 1000.0e6
        }
        resp = self.client.post("/api/radial-profile", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("profile", data)
        self.assertIn("distances_km", data["profile"])

    def test_horizontal_slice_endpoint(self):
        payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "alt_ft": 10000.0,
            "frequency_hz": 1000.0e6,
            "max_range_km": 30.0,
            "num_radials": 24
        }
        resp = self.client.post("/api/horizontal-slice", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["alt_ft"], 10000)
        self.assertIn("geojson", data)
        self.assertIn("coverage_pct", data)

    def test_volumetric_cubes_endpoint(self):
        payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "max_range_km": 20.0,
            "min_alt_ft": 2000.0,
            "max_alt_ft": 6000.0,
            "alt_step_ft": 1000.0,
            "freq_min_hz": 500.0e6,
            "freq_max_hz": 1500.0e6,
            "freq_step_hz": 500.0e6,
            "num_radials": 12,
            "range_step_km": 5.0
        }
        resp = self.client.post("/api/volumetric-cubes", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("overall_cube_coverage_pct", data)
        self.assertIn("frequency_sweep_comparison", data)
        self.assertEqual(len(data["frequency_sweep_comparison"]), 3)

    def test_compound_radius_in_api_endpoints(self):
        # Test radial profile with 75m compound radius
        payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "bearing_deg": 45.0,
            "max_distance_km": 30.0,
            "target_alt_amsl_m": 3000.0,
            "frequency_hz": 1000.0e6,
            "ignored_obstacle_radius_m": 75.0
        }
        resp = self.client.post("/api/radial-profile", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("ignored_obstacle_radius_m"), 75.0)

        # Test horizontal slice with 100m compound radius
        h_payload = {
            "tx_lat": 47.4211,
            "tx_lon": 10.9853,
            "tx_alt_amsl_m": 2962.0,
            "alt_ft": 8000.0,
            "frequency_hz": 1000.0e6,
            "max_range_km": 25.0,
            "num_radials": 24,
            "ignored_obstacle_radius_m": 100.0
        }
        h_resp = self.client.post("/api/horizontal-slice", json=h_payload)
        self.assertEqual(h_resp.status_code, 200)

    def test_session_json_structure_and_roundtrip(self):
        """Verify that a full RadioCov session JSON contains all required subsystems and parameters."""
        session_json = {
            "schema": "radiocov-session-v1",
            "timestamp": "2026-11-27T11:13:19Z",
            "session_name": "Zugspitze_SSR_Radar_Session",
            "transmitter": {
                "lat": 47.4211,
                "lon": 10.9853,
                "alt_amsl_m": 2962.0,
                "location_preset": "Zugspitze Peak"
            },
            "propagation": {
                "max_range_km": 40.0,
                "k_factor": 1.333,
                "compound_mask_enabled": True,
                "ignored_obstacle_radius_m": 50.0
            },
            "technology": {
                "system_key": "SSR_RADAR",
                "channel_index": 0,
                "freq_mhz": 1090.0,
                "channel_overrides": {},
                "custom_budget": {
                    "tx_power_dbm": 54.0,
                    "tx_gain_dbi": 24.0,
                    "rx_gain_dbi": 3.0,
                    "rx_sens_dbm": -90.0,
                    "fade_margin_db": 6.0
                }
            },
            "sweep": {
                "enabled": False,
                "min_mhz": 100,
                "max_mhz": 2000,
                "step_mhz": 300
            },
            "airspace_grid": {
                "min_alt_ft": 1000,
                "max_alt_ft": 25000
            },
            "slices": {
                "alt_slice_ft": 7000,
                "radial_bearing_deg": 95
            },
            "view_3d": {
                "max_alt_ft": 20000,
                "z_scale": 5,
                "show_blocked": True
            }
        }
        self.assertEqual(session_json["schema"], "radiocov-session-v1")
        self.assertIn("transmitter", session_json)
        self.assertIn("propagation", session_json)
        self.assertIn("technology", session_json)
        self.assertIn("slices", session_json)

        # Ensure parameters can directly drive the radial profile calculation
        rp_payload = {
            "tx_lat": session_json["transmitter"]["lat"],
            "tx_lon": session_json["transmitter"]["lon"],
            "tx_alt_amsl_m": session_json["transmitter"]["alt_amsl_m"],
            "bearing_deg": session_json["slices"]["radial_bearing_deg"],
            "max_distance_km": session_json["propagation"]["max_range_km"],
            "target_alt_amsl_m": session_json["slices"]["alt_slice_ft"] * 0.3048,
            "frequency_hz": session_json["technology"]["freq_mhz"] * 1e6,
            "ignored_obstacle_radius_m": session_json["propagation"]["ignored_obstacle_radius_m"]
        }
        resp = self.client.post("/api/radial-profile", json=rp_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["ignored_obstacle_radius_m"], 50.0)


if __name__ == "__main__":
    unittest.main()
