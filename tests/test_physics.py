"""Unit tests for RadioCov pure RF physics and mathematical models."""

import math
import unittest
import numpy as np

from radiocov.config import SPEED_OF_LIGHT, EARTH_MEAN_RADIUS, STANDARD_K_FACTOR
from radiocov.core.physics import RFPhysics


class TestRFPhysics(unittest.TestCase):
    def test_wavelength(self):
        # 300 MHz should be ~1.0 meter
        self.assertAlmostEqual(RFPhysics.wavelength(299792458.0), 1.0, places=4)
        # 1 GHz should be ~0.3 meter
        self.assertAlmostEqual(RFPhysics.wavelength(1.0e9), 0.29979, places=4)
        # Invalid frequency raises
        with self.assertRaises(ValueError):
            RFPhysics.wavelength(0)
        with self.assertRaises(ValueError):
            RFPhysics.wavelength(-1e6)

    def test_effective_earth_radius(self):
        re_std = RFPhysics.effective_earth_radius(4.0 / 3.0)
        expected = EARTH_MEAN_RADIUS * (4.0 / 3.0)
        self.assertAlmostEqual(re_std, expected, places=2)

    def test_earth_bulge(self):
        # Midpoint of 100 km path: d1 = 50 km, d2 = 50 km
        # h = d1*d2 / (2*Re) = (50000 * 50000) / (2 * 6371000 * 4/3) = 2.5e9 / 16989333 ~ 147.15 m
        bulge = RFPhysics.earth_bulge(50000.0, 50000.0, k_factor=4.0 / 3.0)
        self.assertAlmostEqual(bulge, 147.15, delta=1.0)

        # Array input
        d1_arr = np.array([0.0, 50000.0])
        d2_arr = np.array([100000.0, 50000.0])
        bulges = RFPhysics.earth_bulge(d1_arr, d2_arr, k_factor=4.0 / 3.0)
        self.assertEqual(bulges[0], 0.0)
        self.assertAlmostEqual(bulges[1], 147.15, delta=1.0)

    def test_fresnel_radius(self):
        # Path of 10 km (10,000 m) at midpoint d1=5000, d2=5000, frequency 1 GHz (lambda = 0.3 m)
        # r1 = sqrt(lambda * d1 * d2 / (d1 + d2)) = sqrt(0.3 * 25e6 / 10000) = sqrt(750) ~ 27.386 m
        r1 = RFPhysics.fresnel_radius(5000.0, 5000.0, 1.0e9, n=1)
        expected = math.sqrt(0.299792458 * 5000.0 * 5000.0 / 10000.0)
        self.assertAlmostEqual(r1, expected, places=3)
        self.assertAlmostEqual(r1, 27.376, delta=0.1)

        # Clearance ratio
        self.assertAlmostEqual(RFPhysics.fresnel_clearance_ratio(27.376, 27.376), 1.0, places=2)
        self.assertAlmostEqual(RFPhysics.fresnel_clearance_ratio(16.425, 27.376), 0.60, places=2)

    def test_free_space_path_loss(self):
        # 1 km at 1 GHz: FSPL = 20*log10(1000) + 20*log10(1e9) - 147.55 = 60 + 180 - 147.55 = 92.45 dB
        fspl = RFPhysics.free_space_path_loss_db(1000.0, 1.0e9)
        self.assertAlmostEqual(fspl, 92.45, delta=0.2)

        # Distance doubling adds ~6.02 dB
        fspl_2km = RFPhysics.free_space_path_loss_db(2000.0, 1.0e9)
        self.assertAlmostEqual(fspl_2km - fspl, 6.02, delta=0.1)

    def test_knife_edge_diffraction_loss(self):
        # v <= -0.7 should have 0 dB loss
        self.assertEqual(RFPhysics.knife_edge_diffraction_loss_db(-1.0), 0.0)
        self.assertEqual(RFPhysics.knife_edge_diffraction_loss_db(-0.8), 0.0)

        # v = 0 (grazing line of sight) should be ~6 dB
        loss_0 = RFPhysics.knife_edge_diffraction_loss_db(0.0)
        self.assertAlmostEqual(loss_0, 6.02, delta=0.2)

        # v = 1 (clear obstruction) should be ~13.8 dB
        loss_1 = RFPhysics.knife_edge_diffraction_loss_db(1.0)
        self.assertGreater(loss_1, 13.0)

        # Monotonically increasing with positive v
        loss_2 = RFPhysics.knife_edge_diffraction_loss_db(2.0)
        loss_3 = RFPhysics.knife_edge_diffraction_loss_db(3.0)
        self.assertGreater(loss_3, loss_2)
        self.assertGreater(loss_2, loss_1)


if __name__ == "__main__":
    unittest.main()
