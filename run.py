#!/usr/bin/env python3
"""Runner script to launch the RadioCov standalone server and UI."""

import argparse
import sys
from pathlib import Path
import uvicorn

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    parser = argparse.ArgumentParser(description="Start the RadioCov Pure RF Spectrum Coverage Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print("=====================================================================")
    print("📡 RadioCov - Standalone Radio Frequency Spectrum Coverage Tool")
    print("=====================================================================")
    print(f"API & UI running at: http://{args.host}:{args.port}")
    print("=====================================================================")

    uvicorn.run("radiocov.api.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
