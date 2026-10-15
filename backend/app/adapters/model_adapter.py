"""Model Adapter factory and uninitialized placeholder adapter."""
from typing import Any, Dict
from PIL import Image
from .base import BaseInferenceAdapter
from .azure_vision_adapter import AzureVisionAdapter
from .exceptions import ModelUnavailableException
from app.config import settings


class UninitializedModelAdapter(BaseInferenceAdapter):
    """
    Fallback adapter representing an unconfigured model state.
    Raises ModelUnavailableException (subclass of RuntimeError).
    """

    def __init__(self, model_id: str = settings.MODEL_ID):
        self._model_id = model_id
        self._is_loaded = False

    @property
    def model_id(self) -> str:
        return self._model_id

    def load(self) -> None:
        self._is_loaded = False

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        raise ModelUnavailableException(
            f"Model '{self._model_id}' is not configured for inference. "
            "Please configure Azure AI Foundry environment variables (AZURE_AI_ENDPOINT, "
            "AZURE_AI_API_KEY, AZURE_AI_DEPLOYMENT_NAME)."
        )


def get_default_model_adapter() -> BaseInferenceAdapter:
    """
    Factory resolving the active model adapter based on configuration.
    Returns AzureVisionAdapter if Azure AI environment is set up,
    otherwise returns an unconfigured AzureVisionAdapter that raises
    ModelUnavailableException on inference.
    """
    return AzureVisionAdapter()
