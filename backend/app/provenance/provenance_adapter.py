"""Provenance and metadata verification adapter boundary."""
from typing import Dict, Any, List
from app.config import settings


class ProvenanceAdapter:
    """
    Adapter handling C2PA/provenance and metadata checks.
    Marked as conditional/unavailable until tooling is validated.
    """

    def __init__(self, enabled: bool = settings.ENABLE_PROVENANCE_CHECK):
        self.enabled = enabled

    def verify(self, file_path: str) -> Dict[str, Any]:
        """
        Verify provenance credentials.
        Returns explicit status (not_requested, unavailable, not_found, etc.)
        """
        if not self.enabled:
            return {
                "status": "not_requested",
                "checks": []
            }

        # If enabled but toolchain is not yet integrated
        return {
            "status": "unavailable",
            "checks": [
                {
                    "name": "c2pa_manifest",
                    "status": "unavailable",
                    "details": "C2PA verification tooling is not configured in this environment."
                }
            ]
        }
