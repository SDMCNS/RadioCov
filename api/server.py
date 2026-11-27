"""FastAPI REST API server for RadioCov Pure RF Spectrum Coverage."""

import logging
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from radiocov.config import SPECTRUM_BANDS, TECHNOLOGY_PROFILES, PRESET_LOCATIONS, DEFAULT_DEM_TIFF, FT_TO_METERS, METERS_TO_FT
from radiocov.core.terrain import TerrainProvider
from radiocov.core.engine import RFCoverageEngine
from radiocov.core.voxels import VolumetricCoverageGrid
from radiocov.api.models import (
    PointAssessmentRequest,
    RadialProfileRequest,
    HorizontalSliceRequest,
    VolumetricCubesRequest,
    PointCloud3DRequest,
)

logger = logging.getLogger("radiocov.api")

app = FastAPI(
    title="RadioCov API",
    description="Abstract RF Line-of-Sight, 1000-ft Cube Volumetric Coverage & Spectrum Propagation Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Engine Instance
terrain_provider = TerrainProvider(DEFAULT_DEM_TIFF)
engine = RFCoverageEngine(terrain_provider=terrain_provider)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/api/presets")
def get_presets():
    """Retrieve spectrum band presets, technology profiles, and reference geographical locations."""
    return {
        "spectrum_bands": SPECTRUM_BANDS,
        "technology_profiles": TECHNOLOGY_PROFILES,
        "sample_locations": PRESET_LOCATIONS,
        "dem_available": terrain_provider.is_dem_available
    }


@app.post("/api/evaluate-point")
def evaluate_point(req: PointAssessmentRequest):
    """Evaluate point-to-point RF path between Tx and Rx at one or multiple frequencies."""
    try:
        tx_alt_m = req.get_tx_alt_m()
        rx_alt_m = req.get_rx_alt_m()
        res = engine.evaluate_point_to_point(
            tx_lat=req.tx_lat,
            tx_lon=req.tx_lon,
            tx_alt_amsl_m=tx_alt_m,
            rx_lat=req.rx_lat,
            rx_lon=req.rx_lon,
            rx_alt_amsl_m=rx_alt_m,
            frequencies_hz=req.frequencies_hz,
            num_profile_points=req.num_profile_points,
            k_factor=req.k_factor,
            ignored_obstacle_radius_m=req.ignored_obstacle_radius_m
        )
        return res
    except Exception as e:
        logger.error(f"Point evaluation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/radial-profile")
def radial_profile(req: RadialProfileRequest):
    """Compute a vertical cross-section along an azimuth radial."""
    try:
        tx_alt_m = req.get_tx_alt_m()
        target_alt_m = req.get_target_alt_m()
        res = engine.evaluate_radial_profile(
            tx_lat=req.tx_lat,
            tx_lon=req.tx_lon,
            tx_alt_amsl_m=tx_alt_m,
            bearing_deg=req.bearing_deg,
            max_distance_km=req.max_distance_km,
            target_alt_amsl_m=target_alt_m,
            frequency_hz=req.frequency_hz,
            num_profile_points=req.num_profile_points,
            k_factor=req.k_factor,
            ignored_obstacle_radius_m=req.ignored_obstacle_radius_m
        )
        return res
    except Exception as e:
        logger.error(f"Radial profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/horizontal-slice")
def horizontal_slice(req: HorizontalSliceRequest):
    """Generate a 2D coverage slice and GeoJSON boundary at a selected 1,000-ft altitude."""
    try:
        tx_alt_m = req.get_tx_alt_m()
        grid = VolumetricCoverageGrid(
            engine=engine,
            tx_lat=req.tx_lat,
            tx_lon=req.tx_lon,
            tx_alt_amsl_m=tx_alt_m,
            max_range_km=req.max_range_km,
            min_alt_ft=req.alt_ft,
            max_alt_ft=req.alt_ft,
            num_radials=req.num_radials,
            range_step_km=req.range_step_km,
            k_factor=req.k_factor,
            ignored_obstacle_radius_m=req.ignored_obstacle_radius_m
        )
        slice_data = grid.get_horizontal_slice(
            alt_ft=req.alt_ft,
            frequency_hz=req.frequency_hz
        )
        return slice_data
    except Exception as e:
        logger.error(f"Horizontal slice error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/volumetric-cubes")
def volumetric_cubes(req: VolumetricCubesRequest):
    """Compute the 3D dataset in 1,000-ft cubes from min_alt_ft to max_alt_ft across a frequency sweep."""
    try:
        tx_alt_m = req.get_tx_alt_m()
        # Build frequency array from min, max, step
        if req.freq_step_hz <= 0 or req.freq_max_hz < req.freq_min_hz:
            freq_array = [req.freq_min_hz]
        else:
            freq_array = np.arange(req.freq_min_hz, req.freq_max_hz + (req.freq_step_hz / 2.0), req.freq_step_hz).tolist()
            # Limit maximum frequencies in sweep to 15 to keep payload responsive
            if len(freq_array) > 15:
                freq_array = np.linspace(req.freq_min_hz, req.freq_max_hz, 15).tolist()

        grid = VolumetricCoverageGrid(
            engine=engine,
            tx_lat=req.tx_lat,
            tx_lon=req.tx_lon,
            tx_alt_amsl_m=tx_alt_m,
            max_range_km=req.max_range_km,
            min_alt_ft=req.min_alt_ft,
            max_alt_ft=req.max_alt_ft,
            alt_step_ft=req.alt_step_ft,
            num_radials=req.num_radials,
            range_step_km=req.range_step_km,
            k_factor=req.k_factor,
            ignored_obstacle_radius_m=req.ignored_obstacle_radius_m
        )

        matrix_data = grid.compute_coverage_cube_matrix(freq_array)

        # Also precompute horizontal slice summaries at 3 representative altitudes (low, mid, high)
        alts = matrix_data["axes"]["altitudes_ft"]
        sample_alt_indices = [0, len(alts) // 2, len(alts) - 1]
        slices_summary = []
        primary_f = freq_array[0]

        for s_idx in set(sample_alt_indices):
            alt_val = alts[s_idx]
            h_slice = grid.get_horizontal_slice(alt_val, primary_f, cube_matrix_data=matrix_data)
            slices_summary.append({
                "alt_ft": int(alt_val),
                "coverage_pct": h_slice["coverage_pct"]
            })

        overall_pct = round(float(np.mean(matrix_data["results_by_freq"][primary_f]["los_matrix"])) * 100.0, 1)

        return {
            "metadata": matrix_data["metadata"],
            "axes": matrix_data["axes"],
            "frequencies_hz": freq_array,
            "overall_cube_coverage_pct": overall_pct,
            "sample_horizontal_slices": slices_summary,
            "frequency_sweep_comparison": [
                {
                    "frequency_hz": f,
                    "frequency_mhz": round(f / 1e6, 2),
                    "coverage_pct": round(float(np.mean(matrix_data["results_by_freq"][f]["los_matrix"])) * 100.0, 1),
                    "avg_path_loss_db": round(float(np.mean(matrix_data["results_by_freq"][f]["path_loss_db"])), 1)
                }
                for f in freq_array
            ]
        }
    except Exception as e:
        logger.error(f"Volumetric cubes error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/3d-point-cloud")
def point_cloud_3d(req: PointCloud3DRequest):
    """Generate 3D point cloud of 1,000-ft cubes for Three.js WebGL visualization."""
    try:
        tx_alt_m = req.get_tx_alt_m()
        grid = VolumetricCoverageGrid(
            engine=engine,
            tx_lat=req.tx_lat,
            tx_lon=req.tx_lon,
            tx_alt_amsl_m=tx_alt_m,
            max_range_km=req.max_range_km,
            min_alt_ft=req.min_alt_ft,
            max_alt_ft=req.max_alt_ft,
            alt_step_ft=req.alt_step_ft,
            num_radials=req.num_radials,
            range_step_km=req.range_step_km,
            k_factor=req.k_factor,
            ignored_obstacle_radius_m=req.ignored_obstacle_radius_m
        )
        points = grid.get_3d_point_cloud(
            frequency_hz=req.frequency_hz,
            subsample_step=req.subsample_step
        )
        return {
            "tx": {"lat": req.tx_lat, "lon": req.tx_lon, "alt_amsl_ft": req.get_tx_alt_ft(), "alt_amsl_m": tx_alt_m},
            "frequency_hz": req.frequency_hz,
            "total_points": len(points),
            "points": points
        }
    except Exception as e:
        logger.error(f"3D point cloud error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def serve_index():
    """Serve the standalone RadioCov frontend."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h2>RadioCov RF Spectrum Coverage Engine Active</h2><p>Frontend assets not found.</p>")
