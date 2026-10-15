"""Base interface for model adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict
from PIL import Image


class BaseInferenceAdapter(ABC):
    """Abstract interface isolating model-specific inference logic."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier of the underlying model."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load model weights and preprocessors into memory."""
        pass

    @abstractmethod
    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Execute real model inference on the provided Pillow image.
        Returns dictionary with label, score, score_semantics, and raw output.
        Must raise appropriate exceptions on inference failure.
        """
        pass

    async def predict_async(self, image: Image.Image) -> Dict[str, Any]:
        """
        Execute model inference asynchronously.
        Defaults to running synchronous predict() in a worker thread to avoid
        blocking the event loop, or can be overridden by native async clients.
        """
        import asyncio
        return await asyncio.to_thread(self.predict, image)

