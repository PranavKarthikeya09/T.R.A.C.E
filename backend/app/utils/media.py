"""Media validation and processing utilities."""
import io
import os
from typing import Tuple, Optional
from PIL import Image, UnidentifiedImageError
from app.config import settings


def validate_image_upload(filename: Optional[str], content: bytes) -> Tuple[bool, Optional[str], Optional[Image.Image]]:
    """
    Validate that uploaded file is present, within size limit, has an allowed extension,
    and can actually be decoded as a valid image.

    Returns:
        (is_valid, error_code, pil_image)
    """
    if not filename or not content:
        return False, "MISSING_FILE", None

    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        return False, "FILE_TOO_LARGE", None

    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        return False, "UNSUPPORTED_MEDIA_TYPE", None

    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # Verify integrity without decoding entire image yet
        # Re-open because verify() closes or damages the internal buffer state
        image = Image.open(io.BytesIO(content))
        return True, None, image
    except (UnidentifiedImageError, OSError, ValueError):
        return False, "INVALID_IMAGE", None
