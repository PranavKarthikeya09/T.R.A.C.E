"""Provenance and metadata verification adapter boundary."""
from typing import Dict, Any, List
from app.config import settings


class ProvenanceAdapter:
    """
    Adapter boundary for C2PA/provenance checks. Signature verification is not
    implemented; enabled requests therefore report unavailable explicitly.
    """

    def __init__(self, enabled: bool = settings.ENABLE_PROVENANCE_CHECK):
        self.enabled = enabled

    def verify(self, file_path: str) -> Dict[str, Any]:
        """
        Report whether the configured C2PA capability can run.
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "checks": [{
                    "name": "c2pa_manifest",
                    "status": "disabled",
                    "details": "C2PA inspection is disabled by server configuration."
                }]
            }

        # If enabled but toolchain is not yet integrated
        return {
            "status": "unavailable",
            "checks": [
                {
                    "name": "c2pa_manifest",
                    "status": "unavailable",
                "details": "C2PA manifest parsing and cryptographic signature verification are not implemented in this application."
                }
            ]
        }
