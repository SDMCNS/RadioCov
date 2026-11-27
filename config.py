"""Configuration constants, physical parameters, and RF spectrum band definitions."""

import os
from pathlib import Path
from typing import Dict, Any

# Geodetic & Physical Constants
SPEED_OF_LIGHT: float = 299792458.0  # m/s
EARTH_MEAN_RADIUS: float = 6371000.0  # meters (WGS84 spherical equivalent)
STANDARD_K_FACTOR: float = 4.0 / 3.0  # Standard atmospheric refraction multiplier

# Conversion factors
FT_TO_METERS: float = 0.3048
METERS_TO_FT: float = 1.0 / FT_TO_METERS
KM_TO_NM: float = 0.539957
NM_TO_KM: float = 1.0 / KM_TO_NM

# 1000-ft Standard Volumetric Cube
CUBE_ALTITUDE_STEP_FT: float = 1000.0
CUBE_ALTITUDE_STEP_M: float = CUBE_ALTITUDE_STEP_FT * FT_TO_METERS

# Default Paths
PACKAGE_DIR = Path(__file__).resolve().parent
ROOT_PROJECT_DIR = PACKAGE_DIR.parent
DEFAULT_DEM_TIFF = ROOT_PROJECT_DIR / "DEMTIFF" / "eudem_dem_3035_europe.tif"

# Comprehensive Radio Spectrum Bands (Hz)
SPECTRUM_BANDS: Dict[str, Dict[str, Any]] = {
    "VHF_LOW": {
        "name": "VHF Low (Tactical / FM / Mobile)",
        "freq_min_hz": 30.0e6,
        "freq_max_hz": 88.0e6,
        "default_hz": 50.0e6,
        "step_hz": 10.0e6,
        "description": "30-88 MHz: Tactical FM, Land Mobile Radio"
    },
    "FM_BROADCAST": {
        "name": "FM Radio Broadcast",
        "freq_min_hz": 87.5e6,
        "freq_max_hz": 108.0e6,
        "default_hz": 98.0e6,
        "step_hz": 5.0e6,
        "description": "87.5-108 MHz: Commercial Sound Broadcasting"
    },
    "VHF_AIR_MARINE": {
        "name": "VHF Airband / Marine",
        "freq_min_hz": 118.0e6,
        "freq_max_hz": 162.0e6,
        "default_hz": 125.0e6,
        "step_hz": 10.0e6,
        "description": "118-162 MHz: Aviation AM voice, Marine VHF, AIS"
    },
    "UHF_PMR_TETRA": {
        "name": "UHF PMR / TETRA / Emergency",
        "freq_min_hz": 380.0e6,
        "freq_max_hz": 470.0e6,
        "default_hz": 430.0e6,
        "step_hz": 20.0e6,
        "description": "380-470 MHz: Public safety, TETRA, Amateur 70cm"
    },
    "UHF_DVB_CELL_LOW": {
        "name": "UHF TV & 700/800 MHz LTE/5G",
        "freq_min_hz": 470.0e6,
        "freq_max_hz": 860.0e6,
        "default_hz": 700.0e6,
        "step_hz": 50.0e6,
        "description": "470-860 MHz: Broadcast TV, LTE Band 20/28"
    },
    "L_BAND": {
        "name": "L-Band (GNSS / Telemetry / Radar)",
        "freq_min_hz": 1000.0e6,
        "freq_max_hz": 2000.0e6,
        "default_hz": 1400.0e6,
        "step_hz": 100.0e6,
        "description": "1-2 GHz: GPS L1/L2/L5, Galileo, ADS-B, Cellular 1800"
    },
    "S_BAND_WIFI": {
        "name": "S-Band (2.4 GHz WiFi / Radar / Sat)",
        "freq_min_hz": 2000.0e6,
        "freq_max_hz": 4000.0e6,
        "default_hz": 2450.0e6,
        "step_hz": 250.0e6,
        "description": "2-4 GHz: 2.4 GHz ISM/WiFi, S-band Air Traffic Radar"
    },
    "C_BAND_5G": {
        "name": "C-Band (3.5 GHz 5G / Satellite / Weather)",
        "freq_min_hz": 4000.0e6,
        "freq_max_hz": 8000.0e6,
        "default_hz": 5800.0e6,
        "step_hz": 500.0e6,
        "description": "4-8 GHz: 5G Sub-6, 5.8 GHz WiFi/Microwave links, Weather Radar"
    },
    "X_BAND_RADAR": {
        "name": "X-Band (Marine Radar / Satellite)",
        "freq_min_hz": 8000.0e6,
        "freq_max_hz": 12000.0e6,
        "default_hz": 10000.0e6,
        "step_hz": 500.0e6,
        "description": "8-12 GHz: Marine navigation radar, SAR imaging, military comms"
    },
    "KU_BAND": {
        "name": "Ku-Band (Satellite TV & Starlink Downlink)",
        "freq_min_hz": 12000.0e6,
        "freq_max_hz": 18000.0e6,
        "default_hz": 14000.0e6,
        "step_hz": 1000.0e6,
        "description": "12-18 GHz: Satellite broadcast, VSAT terminals, broadband sat"
    },
    "KA_BAND": {
        "name": "Ka-Band (High Throughput Sat / 5G mmWave)",
        "freq_min_hz": 26500.0e6,
        "freq_max_hz": 40000.0e6,
        "default_hz": 28000.0e6,
        "step_hz": 2000.0e6,
        "description": "26.5-40 GHz: 5G mmWave, Ka-band sat links, high-resolution radar"
    }
}

# Standardized Transceiver Technology & Link Budget Profiles
TECHNOLOGY_PROFILES: Dict[str, Dict[str, Any]] = {
    "SSR_RADAR": {
        "id": "SSR_RADAR",
        "name": "SSR Radar / Mode S & ADS-B (1030 / 1090 MHz)",
        "category": "Aviation Surveillance & IFF",
        "standard": "ICAO Annex 10 Vol IV / EUROCAE ED-102B",
        "description": "Secondary Surveillance Radar interrogator (1030 MHz) and transponder / ADS-B reply (1090 MHz)",
        "frequencies": [
            {
                "id": "ssr_uplink",
                "label": "Interrogation Uplink (1030 MHz)",
                "direction": "Ground Interrogator → Aircraft",
                "freq_hz": 1030.0e6,
                "tx_power_dbm": 61.8,  # 1500 W Peak
                "tx_gain_dbi": 27.0,   # Directional SSR array
                "rx_gain_dbi": 3.0,    # Aircraft blade antenna
                "rx_sensitivity_dbm": -74.0,  # ICAO Annex 10 minimum receiver trigger
                "fade_margin_db": 6.0,
                "channel_bw_mhz": 2.0
            },
            {
                "id": "ssr_downlink",
                "label": "Reply Downlink / ADS-B (1090 MHz)",
                "direction": "Aircraft Transponder → Ground Station",
                "freq_hz": 1090.0e6,
                "tx_power_dbm": 54.0,  # 250 W Nominal Class 1/2
                "tx_gain_dbi": 3.0,    # Aircraft blade antenna
                "rx_gain_dbi": 27.0,   # Ground station high-gain antenna
                "rx_sensitivity_dbm": -90.0,  # Ground receiver trigger threshold
                "fade_margin_db": 6.0,
                "channel_bw_mhz": 2.0
            }
        ]
    },
    "AIRBAND_VHF": {
        "id": "AIRBAND_VHF",
        "name": "Aviation VHF Airband AM (Voice & Data)",
        "category": "Aeronautical Communications",
        "standard": "ICAO Annex 10 Vol III / 8.33 kHz & 25 kHz",
        "description": "Civil aviation AM voice communication and VDL Mode 2 air-ground CPDLC data link",
        "frequencies": [
            {
                "id": "airband_voice_enroute",
                "label": "ATC En-Route Voice (125.0 MHz)",
                "direction": "Ground Station ↔ Aircraft (Duplex Voice)",
                "freq_hz": 125.0e6,
                "tx_power_dbm": 44.0,  # 25 W Ground Station
                "tx_gain_dbi": 6.0,    # Collinear array
                "rx_gain_dbi": 2.0,    # Aircraft blade
                "rx_sensitivity_dbm": -107.0, # Voice intelligible limit
                "fade_margin_db": 10.0,
                "channel_bw_mhz": 0.025
            },
            {
                "id": "airband_guard",
                "label": "Emergency Guard Channel (121.5 MHz)",
                "direction": "Distress & Guard Broadcast",
                "freq_hz": 121.5e6,
                "tx_power_dbm": 44.0,  # 25 W
                "tx_gain_dbi": 6.0,
                "rx_gain_dbi": 2.0,
                "rx_sensitivity_dbm": -107.0,
                "fade_margin_db": 10.0,
                "channel_bw_mhz": 0.025
            },
            {
                "id": "airband_vdl2",
                "label": "VDL Mode 2 CPDLC Data (136.975 MHz)",
                "direction": "Air-Ground Packet Data",
                "freq_hz": 136.975e6,
                "tx_power_dbm": 43.0,  # 20 W
                "tx_gain_dbi": 6.0,
                "rx_gain_dbi": 2.0,
                "rx_sensitivity_dbm": -104.0, # BER < 10^-3 limit
                "fade_margin_db": 8.0,
                "channel_bw_mhz": 0.025
            }
        ]
    },
    "LDACS": {
        "id": "LDACS",
        "name": "LDACS (L-band Digital Aeronautical Communications)",
        "category": "Future ATM Broadband Data Link",
        "standard": "ICAO Doc 9871 / SESAR PJ14 / Eurocae ED-262",
        "description": "L-band cellular-like broadband air-ground data link for trajectory-based operations (TBO)",
        "frequencies": [
            {
                "id": "ldacs_fl",
                "label": "Forward Link FL (Ground → Air, 985.5 MHz)",
                "direction": "Ground Station → Aircraft (OFDMA Broadcast)",
                "freq_hz": 985.5e6,
                "tx_power_dbm": 46.0,  # 40 W Ground Station
                "tx_gain_dbi": 10.0,   # Sectorized Ground Array
                "rx_gain_dbi": 3.0,    # Aircraft L-band Blade
                "rx_sensitivity_dbm": -102.0, # QPSK BER < 10^-5
                "fade_margin_db": 8.0,
                "channel_bw_mhz": 0.5
            },
            {
                "id": "ldacs_rl",
                "label": "Reverse Link RL (Air → Ground, 1025.5 MHz)",
                "direction": "Aircraft → Ground Station (OFDMA Access)",
                "freq_hz": 1025.5e6,
                "tx_power_dbm": 43.0,  # 20 W Airborne Transceiver
                "tx_gain_dbi": 3.0,    # Aircraft Blade
                "rx_gain_dbi": 10.0,   # Ground Sector Array
                "rx_sensitivity_dbm": -105.0, # Ground Rx Sensitivity
                "fade_margin_db": 8.0,
                "channel_bw_mhz": 0.5
            }
        ]
    },
    "CELLULAR_5G": {
        "id": "CELLULAR_5G",
        "name": "5G NR Cellular (Sub-6 GHz FR1 - Bands n78 & n28)",
        "category": "Mobile Broadband Network",
        "standard": "3GPP Release 16/17 NR FR1",
        "description": "Commercial 5G New Radio macro site delivering high-throughput mid-band and extended low-band coverage",
        "frequencies": [
            {
                "id": "5g_n78_midband",
                "label": "Band n78 Mid-Band TDD (3500 MHz)",
                "direction": "Macro gNodeB → Smartphone UE",
                "freq_hz": 3500.0e6,
                "tx_power_dbm": 53.0,  # 200 W (64T64R Macro)
                "tx_gain_dbi": 24.0,   # Massive MIMO beamforming array
                "rx_gain_dbi": 0.0,    # Smartphone omni
                "rx_sensitivity_dbm": -98.0, # QAM downlink limit
                "fade_margin_db": 12.0,
                "channel_bw_mhz": 100.0
            },
            {
                "id": "5g_n28_lowband",
                "label": "Band n28 Low-Band FDD (700 MHz)",
                "direction": "Rural Macro gNodeB → UE",
                "freq_hz": 700.0e6,
                "tx_power_dbm": 49.0,  # 80 W Base Station
                "tx_gain_dbi": 16.0,   # Sector Panel
                "rx_gain_dbi": 0.0,
                "rx_sensitivity_dbm": -101.0,
                "fade_margin_db": 10.0,
                "channel_bw_mhz": 20.0
            }
        ]
    },
    "TETRA_PMR": {
        "id": "TETRA_PMR",
        "name": "PMR / TETRA Public Safety & Police (380 / 390 MHz)",
        "category": "Mission-Critical Emergency Services",
        "standard": "ETSI EN 300 392 TETRA Standard",
        "description": "Encrypted emergency trunked radio for police, ambulance, and rescue operations",
        "frequencies": [
            {
                "id": "tetra_dl",
                "label": "Base Station Downlink (390.0 MHz)",
                "direction": "Base Station → Handheld Radio",
                "freq_hz": 390.0e6,
                "tx_power_dbm": 44.0,  # 25 W Base
                "tx_gain_dbi": 6.0,
                "rx_gain_dbi": 1.0,    # Handheld whip antenna
                "rx_sensitivity_dbm": -115.0,
                "fade_margin_db": 10.0,
                "channel_bw_mhz": 0.025
            },
            {
                "id": "tetra_ul",
                "label": "Handheld Uplink (380.0 MHz)",
                "direction": "Handheld Radio → Base Station",
                "freq_hz": 380.0e6,
                "tx_power_dbm": 37.0,  # 5 W Handheld / 10W Vehicle
                "tx_gain_dbi": 1.0,
                "rx_gain_dbi": 6.0,
                "rx_sensitivity_dbm": -118.0, # Base station sensitivity
                "fade_margin_db": 10.0,
                "channel_bw_mhz": 0.025
            }
        ]
    },
    "MICROWAVE_BACKHAUL": {
        "id": "MICROWAVE_BACKHAUL",
        "name": "Point-to-Point Microwave Link (13 GHz Paired FDD)",
        "category": "Telecom Infrastructure Backhaul",
        "standard": "ITU-R F.383 / ETSI Class 4",
        "description": "High-capacity line-of-sight telecommunication trunk link connecting remote towers",
        "frequencies": [
            {
                "id": "mw_subband_low",
                "label": "Low Sub-Band FDD (12.75 GHz)",
                "direction": "Site A → Site B (1024-QAM Trunk)",
                "freq_hz": 12750.0e6,
                "tx_power_dbm": 30.0,  # 1 W ODU
                "tx_gain_dbi": 38.0,   # 1.2m Parabolic Dish
                "rx_gain_dbi": 38.0,   # 1.2m Parabolic Dish
                "rx_sensitivity_dbm": -78.0, # 1024-QAM threshold
                "fade_margin_db": 15.0,
                "channel_bw_mhz": 56.0
            },
            {
                "id": "mw_subband_high",
                "label": "High Sub-Band FDD (13.25 GHz)",
                "direction": "Site B → Site A (1024-QAM Trunk)",
                "freq_hz": 13250.0e6,
                "tx_power_dbm": 30.0,  # 1 W ODU
                "tx_gain_dbi": 38.0,
                "rx_gain_dbi": 38.0,
                "rx_sensitivity_dbm": -78.0,
                "fade_margin_db": 15.0,
                "channel_bw_mhz": 56.0
            }
        ]
    }
}

# Standard Reference Ground Stations & Mountain Peaks
PRESET_LOCATIONS: list[Dict[str, Any]] = [
    {"name": "Zugspitze Peak (Germany/Austria Alps)", "lat": 47.4211, "lon": 10.9853, "alt_amsl_ft": 9718.0, "alt_amsl_m": 2962.0},
    {"name": "Pic du Midi de Bigorre (Pyrenees, France)", "lat": 42.9367, "lon": 0.1411, "alt_amsl_ft": 9439.0, "alt_amsl_m": 2877.0},
    {"name": "Monte Cimone (Apennines, Italy)", "lat": 44.1983, "lon": 10.7006, "alt_amsl_ft": 7103.0, "alt_amsl_m": 2165.0},
    {"name": "Säntis (Appenzell Alps, Switzerland)", "lat": 47.2494, "lon": 9.3433, "alt_amsl_ft": 8209.0, "alt_amsl_m": 2502.0},
    {"name": "Besselberg / Brocken (Harz, Germany)", "lat": 51.7992, "lon": 10.6156, "alt_amsl_ft": 3743.0, "alt_amsl_m": 1141.0},
    {"name": "Feldberg (Black Forest, Germany)", "lat": 47.8739, "lon": 8.0047, "alt_amsl_ft": 4898.0, "alt_amsl_m": 1493.0},
    {"name": "London Crystal Palace Tower (UK)", "lat": 51.4242, "lon": -0.0750, "alt_amsl_ft": 1086.0, "alt_amsl_m": 331.0},
    {"name": "Paris Eiffel Tower (France)", "lat": 48.8584, "lon": 2.2945, "alt_amsl_ft": 1099.0, "alt_amsl_m": 335.0},
]

