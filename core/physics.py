"""Radio Frequency (RF) Physics and Propagation Formulations.

Implements rigorous physical formulas for:
- Wavelength and wave velocity
- Effective Earth curvature and atmospheric refraction (k-factor)
- Fresnel zone ellipsoids (1st Fresnel radius and 60% clearance)
- Free-Space Path Loss (FSPL)
- ITU-R P.526 Knife-edge diffraction attenuation
- Total link path loss and clearance metrics
"""

import math
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

from radiocov.config import SPEED_OF_LIGHT, EARTH_MEAN_RADIUS, STANDARD_K_FACTOR


class RFPhysics:
    """Pure mathematical and physical functions for RF propagation."""

    @staticmethod
    def wavelength(frequency_hz: float) -> float:
        """Calculate RF wavelength in meters: lambda = c / f."""
        if frequency_hz <= 0:
            raise ValueError(f"Frequency must be positive: got {frequency_hz} Hz")
        return SPEED_OF_LIGHT / frequency_hz

    @staticmethod
    def effective_earth_radius(k_factor: float = STANDARD_K_FACTOR) -> float:
        """Calculate effective Earth radius in meters under atmospheric refraction: Re = k * R0."""
        if k_factor <= 0:
            raise ValueError(f"k-factor must be positive: got {k_factor}")
        return EARTH_MEAN_RADIUS * k_factor

    @staticmethod
    def earth_bulge(
        d1_m: Union[float, np.ndarray],
        d2_m: Union[float, np.ndarray],
        k_factor: float = STANDARD_K_FACTOR
    ) -> Union[float, np.ndarray]:
        """Calculate geometric Earth bulge in meters along a path of length (d1 + d2).
        
        Formula: h_bulge = (d1 * d2) / (2 * Re)
        """
        re = RFPhysics.effective_earth_radius(k_factor)
        return (d1_m * d2_m) / (2.0 * re)

    @staticmethod
    def fresnel_radius(
        d1_m: Union[float, np.ndarray],
        d2_m: Union[float, np.ndarray],
        frequency_hz: float,
        n: int = 1
    ) -> Union[float, np.ndarray]:
        """Calculate radius of the n-th Fresnel zone (meters) at distance d1 from Tx and d2 from Rx.
        
        Formula: r_n = sqrt((n * lambda * d1 * d2) / (d1 + d2))
        """
        if frequency_hz <= 0:
            raise ValueError(f"Frequency must be positive: got {frequency_hz}")
        lam = SPEED_OF_LIGHT / frequency_hz
        total_d = d1_m + d2_m
        
        # Handle scalars or numpy arrays
        if isinstance(total_d, np.ndarray):
            safe_d = np.where(total_d <= 0, 1e-9, total_d)
            prod = (n * lam * d1_m * d2_m) / safe_d
            prod = np.maximum(0.0, prod)
            return np.sqrt(prod)
        else:
            if total_d <= 0:
                return 0.0
            prod = (n * lam * d1_m * d2_m) / total_d
            return math.sqrt(max(0.0, prod))

    @staticmethod
    def fresnel_clearance_ratio(clearance_m: float, f1_radius_m: float) -> float:
        """Calculate ratio of clearance to 1st Fresnel zone radius.
        
        A ratio >= 0.60 corresponds to the ITU-R standard for unobstructed LoS (0 dB diffraction loss).
        A negative ratio indicates the obstacle penetrates above the direct line of sight.
        """
        if f1_radius_m <= 1e-6:
            return 1.0 if clearance_m >= 0 else -1.0
        return clearance_m / f1_radius_m

    @staticmethod
    def free_space_path_loss_db(distance_m: Union[float, np.ndarray], frequency_hz: float) -> Union[float, np.ndarray]:
        """Compute Free-Space Path Loss (FSPL) in decibels (dB).
        
        FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
                 = 20*log10(d) + 20*log10(f) - 147.55216
        """
        if frequency_hz <= 0:
            raise ValueError(f"Frequency must be positive: got {frequency_hz}")
            
        freq_term = 20.0 * math.log10(frequency_hz)
        const_term = -147.55216

        if isinstance(distance_m, np.ndarray):
            safe_dist = np.maximum(1.0, distance_m)
            return 20.0 * np.log10(safe_dist) + freq_term + const_term
        else:
            safe_dist = max(1.0, distance_m)
            return 20.0 * math.log10(safe_dist) + freq_term + const_term

    @staticmethod
    def knife_edge_diffraction_loss_db(v: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Compute Knife-Edge Diffraction Loss (dB) using ITU-R P.526 approximation.
        
        v is the dimensionless Fresnel-Kirchhoff diffraction parameter:
            v = h * sqrt(2 * (d1 + d2) / (lambda * d1 * d2))
        where h is obstacle height above line of sight (h > 0 means obstacle blocks LOS).
        """
        if isinstance(v, np.ndarray):
            loss = np.zeros_like(v, dtype=np.float64)
            # Case 1: v <= -0.7 (substantially clear, loss = 0)
            m1 = (v > -0.7) & (v <= 0.0)
            m2 = (v > 0.0) & (v <= 1.0)
            m3 = (v > 1.0) & (v <= 2.4)
            m4 = (v > 2.4)
            
            loss[m1] = 6.02 + 9.11 * v[m1] - 1.27 * (v[m1] ** 2)
            loss[m2] = 6.02 + 9.11 * v[m2] - 1.27 * (v[m2] ** 2)
            loss[m3] = 12.953 + 20.0 * np.log10(v[m3])
            loss[m4] = 16.0 + 20.0 * np.log10(v[m4])
            return np.maximum(0.0, loss)
        else:
            if v <= -0.7:
                return 0.0
            elif v <= 1.0:
                return max(0.0, 6.02 + 9.11 * v - 1.27 * (v ** 2))
            elif v <= 2.4:
                return 12.953 + 20.0 * math.log10(v)
            else:
                return 16.0 + 20.0 * math.log10(v)

    @staticmethod
    def fresnel_kirchhoff_parameter(
        obstacle_height_above_los_m: float,
        d1_m: float,
        d2_m: float,
        frequency_hz: float
    ) -> float:
        """Calculate the dimensionless Fresnel-Kirchhoff parameter v.
        
        Formula: v = h * sqrt((2 * (d1 + d2)) / (lambda * d1 * d2))
        """
        total_d = d1_m + d2_m
        if total_d <= 0 or d1_m <= 0 or d2_m <= 0:
            return 0.0
        lam = SPEED_OF_LIGHT / frequency_hz
        denom = lam * d1_m * d2_m
        if denom <= 0:
            return 0.0
        return obstacle_height_above_los_m * math.sqrt((2.0 * total_d) / denom)

    @staticmethod
    def elevation_angle_deg(
        tx_alt_amsl_m: float,
        rx_alt_amsl_m: float,
        distance_m: float,
        k_factor: float = STANDARD_K_FACTOR
    ) -> float:
        """Calculate geometric elevation angle in degrees from Tx to Rx over curved Earth."""
        if distance_m <= 0:
            return 90.0 if rx_alt_amsl_m >= tx_alt_amsl_m else -90.0
        re = RFPhysics.effective_earth_radius(k_factor)
        # Drop due to earth curvature over distance
        curv_drop = (distance_m * distance_m) / (2.0 * re)
        h_diff = (rx_alt_amsl_m - tx_alt_amsl_m) - curv_drop
        return math.degrees(math.atan2(h_diff, distance_m))
