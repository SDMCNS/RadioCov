"""RadioCov - Pure Radio Frequency Spectrum Line-of-Sight & Volumetric Coverage Library.

Abstract RF coverage assessment tool considering frequency, physical obstacles,
atmospheric refraction, and 3D volumetric airspace/space cubes (1,000-ft intervals).
"""

__version__ = "1.0.0"

from radiocov.config import (
    SPEED_OF_LIGHT,
    EARTH_MEAN_RADIUS,
    STANDARD_K_FACTOR,
    FT_TO_METERS,
    METERS_TO_FT,
    SPECTRUM_BANDS,
)
from radiocov.core.physics import RFPhysics
from radiocov.core.terrain import TerrainProvider
from radiocov.core.engine import RFCoverageEngine
from radiocov.core.voxels import VolumetricCoverageGrid, SliceType

__all__ = [
    "SPEED_OF_LIGHT",
    "EARTH_MEAN_RADIUS",
    "STANDARD_K_FACTOR",
    "FT_TO_METERS",
    "METERS_TO_FT",
    "SPECTRUM_BANDS",
    "RFPhysics",
    "TerrainProvider",
    "RFCoverageEngine",
    "VolumetricCoverageGrid",
    "SliceType",
]
