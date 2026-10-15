"""Result Composer and T.R.A.C.E. Alert Logic."""
from typing import Dict, Any, List
from app.schemas.analysis import TraceAlert


class ResultComposer:
    """
    Composes normalized results and contextual T.R.A.C.E. alerts
    grounded in available evidence and communicating uncertainty.
    """

    STANDARD_LIMITATIONS: List[str] = [
        "Automated AI detection outputs are statistical indicators, not definitive proof of manipulation or authenticity.",
        "Absence of detected artifacts does not guarantee that the media is genuine.",
        "Absence of provenance credentials does not imply manipulation, nor do valid credentials guarantee truthful real-world content."
    ]

    @staticmethod
    def compose_alert(ai_result: Dict[str, Any], provenance_result: Dict[str, Any]) -> TraceAlert:
        """
        Derive alert level and message from completed checks.
        Never declares certainty.
        """
        ai_status = ai_result.get("status")
        prov_status = (provenance_result.get("status") or "").lower()

        if ai_status != "completed":
            return TraceAlert(
                level="inconclusive",
                message="Automated detection could not be completed. Independent verification recommended."
            )

        # Check for cryptographic tampering or failure in provenance credentials
        if prov_status in ("invalid", "tampered"):
            return TraceAlert(
                level="caution",
                message="Caution: Provenance credentials failed verification or indicate tampering. Media integrity cannot be trusted."
            )

        label = (ai_result.get("label") or "").lower()

        # Handle 'potential_manipulation', 'manipulated', 'synthetic', 'fake', 'deepfake'
        if "manipulat" in label or "fake" in label or "synthetic" in label or "deepfake" in label:
            return TraceAlert(
                level="caution",
                message="Caution: Potential media manipulation detected by automated analysis. Verify original source before trusting or sharing."
            )
        elif "authentic" in label or "real" in label:
            return TraceAlert(
                level="info",
                message="No strong signs of manipulation detected by the available checks. Authenticity cannot be definitively established."
            )
        else:
            return TraceAlert(
                level="inconclusive",
                message="Inconclusive: Automated analysis returned ambiguous indicators. Further verification recommended."
            )
