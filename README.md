# RadioCov: Pure RF Spectrum Coverage & 3D Volumetric Airspace Library

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)](https://threejs.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-brightgreen.svg)](https://leafletjs.com/)
[![ITU-R P.526](https://img.shields.io/badge/Standard-ITU--R%20P.526--15-orange.svg)](https://www.itu.int/rec/R-REC-P.526/en)

**RadioCov** is a high-performance, domain-agnostic Python library and interactive web platform for assessing **Radio Frequency (RF) Line of Sight (LoS)**, **electromagnetic wave propagation**, **link budget feasibility**, and **3D volumetric airspace coverage in 1,000-ft cubes**.

Unlike conventional coverage tools tightly coupled to specific civil radar or cellular systems, RadioCov treats any transceiver as an arbitrary point in 3D space $(\text{Lat}, \text{Lon}, \text{AMSL})$ operating from **30 MHz (VHF) up to 40 GHz (Ka-band / mmWave)**. It directly evaluates true wave mechanics—including spherical Earth bulge, atmospheric refraction ($k$-factor), Fresnel zone ellipsoids, ITU-R P.526 knife-edge diffraction, and sub-meter terrain blockage—against high-resolution Digital Elevation Models (e.g., 25-meter EU-DEM).

> [!NOTE]
> For the complete mathematical derivations and physics formulations, see the companion document:
> 📘 **[FORMULAE.md](FORMULAE.md)**

---

## 📸 Screenshots

### 3D Volumetric Airspace Cubes (WebGL)
Interactive Three.js rendering of discrete 1,000-ft airspace cubes, showing LOS-cleared (green) vs. terrain-blocked shadow (red) volumes, altitude ceiling clipping, vertical exaggeration, and 3D North compass.

![3D Volumetric Airspace Cubes](screenshots/3d%20View.png)

### 2D Horizontal Coverage Slice
Dynamic coverage contour at any 1,000-ft flight level rendered on Leaflet with numbered range rings and synchronized radial azimuth indicator.

![2D Horizontal Coverage Slice](screenshots/Horizontal%20profile%20view.png)

### 2D Vertical Radial Cross-Section
Cross-sectional ray trace along a selected azimuth showing Earth bulge ($k = 1.33$), EU-DEM terrain profile, direct LOS ray, 1st Fresnel zone ($F_1$) envelope, compound mask, and sub-meter blockage localization.

![2D Vertical Radial Cross-Section](screenshots/Vertical%20Profile%20view.png)

### Transceiver Technology & Link Budget Assessment
Bidirectional link budget evaluation (e.g., SSR / Mode S 1030 MHz uplink vs. 1090 MHz ADS-B downlink) with MAPL, FSPL, ITU-R P.526 diffraction loss, link margin, and asymmetry diagnostics.

![Technology and Link Budget Assessment](screenshots/Link%20Budget%20view.png)

### In-App RF Physics & Formulae Reference
Built-in physics modal documenting atmospheric refraction, Earth bulge geometry, Fresnel zone clearance, and ITU-R P.526-15 formulations.

![RF Physics and Formulae Modal](screenshots/Formulae%20modal.png)

---

## 🌟 Key Features

1. **True Wave Mechanics & Earth Curvature**:
   - Atmospheric refraction with adjustable equivalent Earth radius factor ($k = 4/3 \approx 1.333$ standard, sub-refraction, and super-refraction).
   - Spherical Earth bulge calculation: $h_{\text{bulge}} = \frac{d_1 d_2}{2 k R_0}$.
   - First Fresnel zone ($F_1$) ellipsoid geometry and standard $0.6 \cdot F_1$ clearance verification.
   - Rigorous **ITU-R Recommendation P.526-15** single knife-edge diffraction attenuation parameter $v$ and path loss curves.
   - Free Space Path Loss (FSPL) in dB via Friis transmission modeling.

2. **Sub-Meter Blockage Localization & Near-Field Compound Masking**:
   - Zero-crossing root finding along ray paths to pinpoint the exact distance ($\text{km}$) and altitude ($\text{m AMSL}$) of physical terrain blockages.
   - Configurable **Compound / Position Confusion Radius** ($25\text{--}100\text{ m}$) to suppress false near-field ground blockages caused by DEM pixel alignment under tower masts.

3. **Transceiver Technology & Link Budget Assessment**:
   - Pre-configured, standards-compliant technology profiles:
     - **Aviation VHF Airband AM** (118–137 MHz, 25 W, ICAO Annex 10)
     - **Secondary Surveillance Radar / ADS-B** (1030 / 1090 MHz, 250 W / 1500 W peak, EUROCAE ED-102B)
     - **5G NR C-Band** (3.5 GHz, 40 W, 3GPP Rel 16/17)
     - **LDACS** (L-band Digital Aeronautical Comms System, 960–1164 MHz)
     - **Microwave Backhaul** (11 GHz, high-gain parabolic links)
   - Real-time **Maximum Allowable Path Loss (MAPL)** and **Link Margin ($\Delta M$)** calculation.

4. **1,000-ft Airspace Voxel Cubes**:
   - Volumetric 3D airspace partitioning into discrete **1,000-foot vertical increments** ($304.8\text{ m}$), matching international ICAO Flight Levels (FL010–FL600).
   - Full 3D array generation across azimuth, radial distance, and altitude.

5. **Multi-Perspective Visualizers**:
   - **Interactive 2D Horizontal Slice**: Dynamic coverage contour at any 1,000-ft flight level with labeled range rings and Leaflet map rendering.
   - **Interactive 2D Vertical Profile**: Cross-sectional ray tracing along any azimuth radial showing curved Earth, terrain profile, direct ray, $F_1$ envelope, sub-meter blockage flags, and receiver altitude callout.
   - **Interactive 3D WebGL (Three.js)**: 3D volumetric rendering of 1,000-ft cubes, color-coded by altitude layer, featuring:
     - 3D Compass / North Arrow marker.
     - User-adjustable **Maximum Altitude Ceiling** to hide upper cube layers and inspect low-level valley propagation.
     - Variable vertical exaggeration ($1.0\times\text{ to }10.0\times$).
     - Turntable auto-rotation and OrbitControls navigation.

6. **Dynamic Slices Synchronization**:
   - Adjusting the altitude slider or azimuth radial instantaneously synchronizes the 2D horizontal slice, vertical radial profile, and 3D direct ray.

7. **Multi-Band Spectrum Sweep**:
   - Frequency sweep engine ($f_{\min}, f_{\max}, \Delta f$) from 30 MHz to 40 GHz to analyze frequency-dependent diffraction penetration and path loss curves.

8. **Session Management (JSON Export & Import)**:
   - Full serialization and restoration of complete assessment sessions (transmitter parameters, compound masking, technology profiles, custom link budget, airspace grid dimensions, and 3D view settings).

---

## 🏗️ Architecture & Directory Structure

```
radiocov/
├── api/
│   ├── models.py           # Pydantic v2 schemas for requests & responses
│   └── server.py           # FastAPI endpoints (/api/...)
├── core/
│   ├── engine.py           # Core RFCoverageEngine: point-to-point, radials, slices
│   ├── geo.py              # Geodesic & coordinate utilities
│   ├── physics.py          # Pure mathematical models (Fresnel, FSPL, ITU-R P.526, Earth bulge)
│   ├── terrain.py          # Out-of-core high-speed elevation sampling via Rasterio & EU-DEM
│   └── voxels.py           # 3D 1,000-ft volumetric cube grid generation
├── frontend/
│   ├── app.js              # Leaflet & Three.js UI controller, state manager, session I/O
│   ├── index.html          # Professional multi-panel dark-mode GUI
│   └── style.css           # Styling, responsive layout, controls
├── screenshots/            # Web UI screenshots for documentation
├── tests/
│   ├── test_api.py         # REST API endpoint verification tests
│   ├── test_engine.py      # Coverage engine, blockage precedence & compound masking tests
│   └── test_physics.py     # Pure mathematical validation against ITU-R P.526 benchmarks
├── cli.py                  # Standalone Command-Line Interface
├── config.py               # Constants, spectrum bands, technology profiles, default paths
├── run.py                  # Uvicorn application server entry point
├── FORMULAE.md             # Detailed mathematical & physics reference
└── README.md               # Library and user guide
```

---

## ⚙️ Installation & Setup

### Prerequisites

- **Python 3.10+** (tested on Python 3.10, 3.11, and 3.12).
- **GDAL & Rasterio** (for reading European EU-DEM GeoTIFF files).
- **European Digital Elevation Model (EU-DEM v1.1 25m)** GeoTIFF.

### 1. Clone Repository & Create Virtual Environment

```bash
git clone https://github.com/your-org/geodata.git
cd geodata

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

Install all core dependencies:

```bash
pip install -r requirements.txt
```

*Or install required packages directly:*
```bash
pip install fastapi uvicorn rasterio numpy pydantic pyproj scipy
```

### 3. Configure Digital Elevation Model (DEM)

RadioCov expects a GeoTIFF elevation raster. By default, it looks for:
```
DEMTIFF/eudem_dem_3035_europe.tif
```
If your DEM is located elsewhere, you can configure it via:
1. **Environment Variable**:
   ```bash
   export EUDEM_TIFF_PATH="/path/to/your/dem.tif"
   ```
2. **Command-Line Flag**:
   ```bash
   python radiocov/run.py --dem-path "/path/to/your/dem.tif"
   ```
3. **`config.py`**:
   Edit `DEFAULT_DEM_TIFF` in `radiocov/config.py`.

---

## 🚀 Running the Application

### 1. Launch the Interactive Web GUI

```bash
python radiocov/run.py --port 8080 --reload
```
Open **`http://localhost:8080`** in any modern web browser.

### 2. Command-Line Interface (CLI)

RadioCov includes a comprehensive CLI tool for automated headless runs and batch exports:

```bash
# Evaluate a point-to-point link between Zugspitze and Munich
python -m radiocov.cli evaluate-point \
  --tx-lat 47.4211 --tx-lon 10.9853 --tx-alt 2962 \
  --rx-lat 48.1351 --rx-lon 11.5820 --rx-alt 1500 \
  --freq 1090

# Calculate 3D coverage cubes out to 50 km across 1,000-ft layers (FL010 to FL250)
python -m radiocov.cli volumetric-cubes \
  --tx-lat 47.4211 --tx-lon 10.9853 --tx-alt 2962 \
  --range-km 50 --min-alt-ft 1000 --max-alt-ft 25000 \
  --freq 1030 --output coverage_cubes.json

# Extract a 2D horizontal slice at 10,000 ft AMSL
python -m radiocov.cli horizontal-slice \
  --tx-lat 47.4211 --tx-lon 10.9853 --tx-alt 2962 \
  --range-km 60 --alt-ft 10000 --freq 125 --output slice_10000ft.geojson
```

---

## 🖥️ Interactive Web UI Walkthrough

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ RADIOCOV - Pure RF Coverage & 3D Volumetric Airspace Engine                │
├─────────────────────┬───────────────────────────────────────────────────────┤
│ SIDEBAR CONTROLS    │ TAB 1: Transceiver & Link Budget Assessment           │
│                     │ TAB 2: Multi-Band Spectrum Sweep                      │
│ 1. Transceiver Siting│ TAB 3: 2D Horizontal Coverage Slice                   │
│    • Presets & Coords│ TAB 4: 2D Vertical Radial Cross-Section               │
│    • Mast Height (m)│ TAB 5: 3D Volumetric Airspace Cubes (Three.js)        │
│                     ├───────────────────────────────────────────────────────┤
│ 2. Propagation      │ LEAFLET 2D MAP / THREE.JS 3D CANVAS VIEW              │
│    • k-factor (4/3) │ • Color-coded 1,000-ft altitude layers                │
│    • Compound Mask  │ • Numbered distance rings (10 km, 20 km...)          │
│      (25-100m)      │ • 3D Compass & North marker                           │
│                     │ • Max altitude ceiling filter slider                  │
│ 3. Session I/O      │ • Interactive terrain blockage indicators             │
│    • Export JSON    │                                                       │
│    • Import JSON    │                                                       │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

### 1. Transceiver & Compound Masking
- Select a preset station (e.g., *Zugspitze*, *Pic du Midi*, *Hoher Sonnblick*, *Mont Blanc*) or enter custom coordinates $(\phi, \lambda)$ and ground elevation.
- **Compound / Position Confusion Toggle**: Enable to ignore terrain obstacles within $25\text{--}100\text{ m}$ of the mast, eliminating DEM pixel boundary artifacts.

### 2. Technology & Link Budget Assessment
- Select a standard technology profile:
  - **Aviation VHF Airband AM** (125.0 MHz voice, 121.5 MHz emergency, 136.975 MHz VDL2 CPDLC data)
  - **SSR Mode S / ADS-B** (1030 MHz uplink, 1090 MHz downlink)
  - **5G NR Sub-6 C-Band** (3500 MHz downlink)
  - **LDACS Aeronautical Data Link** (960–1164 MHz)
  - **Custom Link Budget**: Define custom $P_{\text{tx}}$, $G_{\text{tx}}$, $G_{\text{rx}}$, sensitivity, and fade margin.
- The UI computes **EIRP**, **MAPL**, **Total Path Loss**, and **Link Margin ($\Delta M$)** with clear pass/fail status.

### 3. Interactive Slices (2D Map & Profile)
- **Horizontal Slice**: Select any flight level in 1,000-ft increments. The engine renders the full polygon coverage footprint with small numbered distance rings on Leaflet.
- **Vertical Profile**: Select an azimuth radial ($0^\circ\text{ to }359^\circ$). View the true curved Earth geometry, terrain silhouette, direct ray, $0.6 F_1$ Fresnel envelope, and the exact sub-meter blockage distance callout (e.g. `Blocked by terrain at 29.75 km (1,842 m AMSL)`).
- **Live Sync**: Moving the altitude slider updates both the 2D slice and the vertical profile simultaneously.

### 4. 3D Volumetric Airspace Cubes
- Direct WebGL rendering with Three.js.
- Each cube represents a discrete **1,000-ft $\times$ polar-arc airspace cell**.
- **Max Altitude Filter**: A slider enables clipping high-altitude cubes so you can inspect low-altitude valley shielding without obstruction.
- **3D Compass**: A red North-pointing 3D arrow with cardinal labels ($N, E, S, W$) maintains orientation during rotation and zoom.
- Adjust vertical exaggeration from $1.0\times$ up to $10.0\times$.

### 5. Session JSON Export & Import
- Click **Export Session** to download a `.json` snapshot of all active parameters (transmitter, antenna height, technology, link budget, frequency sweep, compound masking, and slice selections).
- Click **Import Session** to restore a previous session instantly.

---

## 🐍 Programmatic Python API

RadioCov can be imported as a standalone library into any Python analytics or simulation script.

```python
from radiocov import RFCoverageEngine, VolumetricCoverageGrid, TerrainProvider, RFPhysics

# 1. Initialize Terrain Provider & Coverage Engine
terrain = TerrainProvider()  # Loads EU-DEM GeoTIFF
engine = RFCoverageEngine(terrain_provider=terrain)

# 2. Point-to-Point Path Analysis
result = engine.evaluate_point_to_point(
    tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,  # Zugspitze
    rx_lat=48.1351, rx_lon=11.5820, rx_alt_amsl_m=1500.0,  # Munich 1500m AMSL
    frequencies_hz=[125.0e6, 1090.0e6, 3500.0e6],
    k_factor=1.333,
    compound_mask_m=50.0  # Mask near-field mast compound
)

print(f"Distance: {result['distance_km']:.2f} km")
print(f"Optical LoS: {result['optical_los']}")
print(f"Radio LoS (0.6 F1): {result['radio_los']}")
print(f"Diffraction Loss at 1090 MHz: {result['frequencies'][1090.0e6]['diffraction_loss_db']:.2f} dB")
print(f"Total Path Loss: {result['frequencies'][1090.0e6]['total_path_loss_db']:.2f} dB")

# 3. Radial Cross-Section
radial = engine.calculate_radial_profile(
    tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,
    bearing_deg=45.0,
    max_range_km=80.0,
    rx_alt_amsl_m=3000.0,
    frequency_hz=1090.0e6,
    num_samples=250,
    compound_mask_m=50.0
)

if radial["is_blocked"]:
    print(f"Path is blocked at {radial['first_blockage_km']:.2f} km!")

# 4. Generate 1,000-ft Volumetric Cube Grid
grid = VolumetricCoverageGrid(
    engine=engine,
    tx_lat=47.4211, tx_lon=10.9853, tx_alt_amsl_m=2962.0,
    max_range_km=60.0,
    min_alt_ft=1000.0,
    max_alt_ft=30000.0,
    alt_step_ft=1000.0,
    num_radials=72
)

# Extract a 2D horizontal slice at 12,000 ft AMSL
slice_12k = grid.get_horizontal_slice(alt_ft=12000.0, frequency_hz=1090.0e6)
print(f"Coverage Area at 12,000 ft: {slice_12k['coverage_km2']:.1f} km²")
```

---

## 📡 REST API Reference

The FastAPI backend exposes clean, fully typed endpoints:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/presets` | Preset mountain summits, high towers, and spectrum band definitions |
| `GET` | `/api/technology-profiles` | Standardized transceiver profiles (Airband, SSR, 5G, LDACS, etc.) |
| `POST` | `/api/evaluate-point` | Point-to-point link evaluation, clearance, FSPL, and diffraction loss |
| `POST` | `/api/radial-profile` | 2D vertical cross-section along an azimuth radial |
| `POST` | `/api/horizontal-slice` | 2D horizontal coverage footprint & GeoJSON polygon at a 1,000-ft altitude |
| `POST` | `/api/volumetric-cubes` | Full 3D 1,000-ft cube dataset across user-defined frequency sweep |
| `POST` | `/api/3d-point-cloud` | Optimized 3D point cloud for WebGL Three.js rendering |

### Example Request (`POST /api/evaluate-point`)

```json
{
  "tx_lat": 47.4211,
  "tx_lon": 10.9853,
  "tx_alt_amsl_m": 2962.0,
  "rx_lat": 48.1351,
  "rx_lon": 11.5820,
  "rx_alt_amsl_m": 1500.0,
  "frequencies_hz": [1030000000, 1090000000],
  "k_factor": 1.333333,
  "compound_mask_m": 50.0
}
```

---

## 🧪 Testing & Verification

RadioCov includes a comprehensive test suite validating physics implementations against ITU-R P.526 benchmarks, API contract compliance, and engine edge cases:

```bash
# Run all tests using Python unittest
python -m unittest discover radiocov/tests -v
```

The test suite covers:
- **`test_physics.py`**: Validates FSPL, Fresnel radius, grazing incidence knife-edge loss ($6.02\text{ dB}$ at $v=0$), and Earth bulge.
- **`test_engine.py`**: Verifies point-to-point path evaluation, physical blockage precedence over underground receivers, sub-meter blockage distance interpolation, and compound masking.
- **`test_api.py`**: Verifies all FastAPI endpoints, request validation, and JSON responses.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
