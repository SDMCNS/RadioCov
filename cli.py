"""Command-Line Interface (CLI) for RadioCov Pure RF Spectrum Coverage."""

import argparse
import json
import sys
from pathlib import Path

from radiocov.config import CUBE_ALTITUDE_STEP_FT, STANDARD_K_FACTOR
from radiocov.core.terrain import TerrainProvider
from radiocov.core.engine import RFCoverageEngine
from radiocov.core.voxels import VolumetricCoverageGrid


def main():
    parser = argparse.ArgumentParser(
        description="RadioCov - Pure RF Spectrum Line-of-Sight & Volumetric Coverage CLI"
    )
    parser.add_argument("--tx-lat", type=float, required=True, help="Transmitter Latitude (°N)")
    parser.add_argument("--tx-lon", type=float, required=True, help="Transmitter Longitude (°E)")
    parser.add_argument("--tx-alt-ft", type=float, default=None, help="Transmitter Altitude AMSL in feet (default: 9,718 ft)")
    parser.add_argument("--tx-alt", type=float, default=None, help="Transmitter Altitude AMSL in meters (fallback)")
    parser.add_argument("--range-km", type=float, default=100.0, help="Maximum coverage radius (km)")
    parser.add_argument("--min-alt-ft", type=float, default=1000.0, help="Min altitude in feet AMSL")
    parser.add_argument("--max-alt-ft", type=float, default=20000.0, help="Max altitude in feet AMSL")
    parser.add_argument("--alt-step-ft", type=float, default=CUBE_ALTITUDE_STEP_FT, help="Cube height step (default 1000 ft)")
    parser.add_argument("--freq-mhz", type=float, default=1090.0, help="Frequency in MHz (or comma-separated sweep)")
    parser.add_argument("--freq-sweep", type=str, default="", help="Frequency sweep: min,max,step in MHz (e.g. 100,2000,200)")
    parser.add_argument("--k-factor", type=float, default=STANDARD_K_FACTOR, help="Atmospheric refraction factor (default 1.333)")
    parser.add_argument("--radials", type=int, default=48, help="Number of azimuth radials")
    parser.add_argument("--output", type=str, default="", help="Output JSON file path")
    parser.add_argument("--dem-path", type=str, default="", help="Custom GeoTIFF DEM path")

    args = parser.parse_args()

    # Parse frequencies
    if args.freq_sweep:
        parts = [float(x.strip()) for x in args.freq_sweep.split(",")]
        if len(parts) == 3:
            import numpy as np
            freqs_hz = np.arange(parts[0] * 1e6, (parts[1] + parts[2]/2.0) * 1e6, parts[2] * 1e6).tolist()
        else:
            freqs_hz = [parts[0] * 1e6]
    else:
        freqs_hz = [args.freq_mhz * 1e6]

    if args.tx_alt_ft is not None:
        tx_alt_ft = args.tx_alt_ft
        tx_alt_m = tx_alt_ft * 0.3048
    elif args.tx_alt is not None:
        tx_alt_m = args.tx_alt
        tx_alt_ft = tx_alt_m * 3.28084
    else:
        tx_alt_ft = 9718.0
        tx_alt_m = 2962.0

    print("=====================================================================")
    print("📡 RadioCov - RF Spectrum Volumetric Coverage Assessment")
    print("=====================================================================")
    print(f"Transmitter: ({args.tx_lat:.4f}°N, {args.tx_lon:.4f}°E) at {tx_alt_ft:,.0f} ft ({tx_alt_m:.1f} m) AMSL")
    print(f"Coverage Range: {args.range_km} km | Radials: {args.radials} | k-factor: {args.k_factor:.2f}")
    print(f"Airspace Cubes: {args.min_alt_ft:,.0f} ft to {args.max_alt_ft:,.0f} ft (step: {args.alt_step_ft:,.0f} ft)")
    print(f"Frequencies: {[f'{round(f/1e6)} MHz' for f in freqs_hz]}")

    terrain = TerrainProvider(tiff_path=args.dem_path if args.dem_path else None)
    engine = RFCoverageEngine(terrain_provider=terrain, k_factor=args.k_factor)

    grid = VolumetricCoverageGrid(
        engine=engine,
        tx_lat=args.tx_lat,
        tx_lon=args.tx_lon,
        tx_alt_amsl_ft=tx_alt_ft,
        tx_alt_amsl_m=tx_alt_m,
        max_range_km=args.range_km,
        min_alt_ft=args.min_alt_ft,
        max_alt_ft=args.max_alt_ft,
        alt_step_ft=args.alt_step_ft,
        num_radials=args.radials,
        k_factor=args.k_factor
    )

    print("\nComputing 3D 1,000-ft cube matrix across terrain & frequency spectrum...")
    data = grid.compute_coverage_cube_matrix(freqs_hz)

    # Display results summary
    print("\n--- Coverage Summary by Altitude Layer (1,000-ft Cubes) ---")
    primary_f = freqs_hz[0]
    for alt_ft in grid.altitude_levels_ft[::2]:  # every 2nd layer
        h_slice = grid.get_horizontal_slice(alt_ft, primary_f, cube_matrix_data=data)
        print(f"  Alt {int(alt_ft):>6,} ft: {h_slice['coverage_pct']:>5.1f}% coverage (Avg Range: {h_slice['geojson']['features'][0]['properties']['avg_range_km']:>5.1f} km)")

    if len(freqs_hz) > 1:
        print("\n--- Frequency Sweep Comparison ---")
        for f in freqs_hz:
            res = data["results_by_freq"][f]
            avg_loss = float(data["results_by_freq"][f]["path_loss_db"].mean())
            pct = float(data["results_by_freq"][f]["los_matrix"].mean()) * 100.0
            print(f"  {round(f/1e6):>5} MHz: {pct:>5.1f}% coverage | Avg Path Loss: {avg_loss:>5.1f} dB")

    if args.output:
        out_path = Path(args.output)
        out_dict = {
            "metadata": data["metadata"],
            "axes": data["axes"],
            "frequencies_hz": data["frequencies_hz"]
        }
        with open(out_path, "w") as fp:
            json.dump(out_dict, fp, indent=2)
        print(f"\nSaved output dataset to {out_path.resolve()}")


if __name__ == "__main__":
    main()
