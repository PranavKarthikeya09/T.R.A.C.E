"""Placeholder Model Adapter for Phase 1 setup."""
from typing import Any, Dict
from PIL import Image
from .base import BaseInferenceAdapter
from app.config import settings


class UninitializedModelAdapter(BaseInferenceAdapter):
    """
    Placeholder adapter representing the model adapter boundary before
    model selection and validation in Phase 2.
    """

    def __init__(self, model_id: str = settings.MODEL_ID):
        self._model_id = model_id
        self._is_loaded = False

    @property
    def model_id(self) -> str:
        return self._model_id

    def load(self) -> None:
        """
        Model loading will be implemented in Phase 2 once the pretrained
        model is chosen and validated.
        """
        # Explicitly not loaded in Phase 1 setup
        self._is_loaded = False

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Placeholder predicting method. Raises RuntimeError to prevent
        fabricated outputs prior to model integration.
        """
        raise RuntimeError(
            f"Model '{self._model_id}' is not loaded. Model selection and integration occur in Phase 2."
        )
