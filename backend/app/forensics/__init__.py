"""T.R.A.C.E. Forensics Analysis Package.

Contains standalone, deterministic forensic signal processing and metadata inspection modules.
"""
from .metadata_parser import extract_image_metadata, ImageMetadataResult, METADATA_DISCLAIMER
from .ela import (
    generate_ela_map,
    ELAResult,
    ELA_DISCLAIMER,
    ELA_LIMITATIONS,
    DEFAULT_MAX_VISUALIZATION_DIMENSION,
)

__all__ = [
    "extract_image_metadata",
    "ImageMetadataResult",
    "METADATA_DISCLAIMER",
    "generate_ela_map",
    "ELAResult",
    "ELA_DISCLAIMER",
    "ELA_LIMITATIONS",
    "DEFAULT_MAX_VISUALIZATION_DIMENSION",
]
