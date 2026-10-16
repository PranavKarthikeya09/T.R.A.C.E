"""Image Metadata and EXIF Forensic Inspector.

Provides standalone, deterministic metadata inspection using native Pillow capabilities.
Extracts camera hardware profiles, capture timestamps, editing software tags, and
orientation, while safely handling missing or malformed metadata.
"""
from dataclasses import dataclass, field, asdict
import io
import logging
from typing import Any, Dict, List, Optional, Union
from PIL import Image, ExifTags, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Standard EXIF Orientation tag code and value mappings (Exif tag 274 / 0x0112)
ORIENTATION_DESCRIPTIONS: Dict[int, str] = {
    1: "Horizontal (normal)",
    2: "Mirrored horizontal",
    3: "Rotated 180 degrees",
    4: "Mirrored vertical",
    5: "Mirrored horizontal and rotated 270 degrees CW",
    6: "Rotated 90 degrees CW",
    7: "Mirrored horizontal and rotated 90 degrees CW",
    8: "Rotated 270 degrees CW",
}

# Substrings flagging known image editing and post-processing software
EDITING_SOFTWARE_KEYWORDS: List[str] = [
    "photoshop",
    "lightroom",
    "gimp",
    "affinity",
    "pixelmator",
    "snapseed",
    "canva",
    "vsco",
    "paint.net",
    "coreldraw",
    "photopea",
]

# Substrings flagging generative AI synthesis tools and pipelines
GENERATIVE_TOOL_KEYWORDS: List[str] = [
    "midjourney",
    "stable diffusion",
    "stablediffusion",
    "dall-e",
    "dalle",
    "comfyui",
    "automatic1111",
    "novelai",
    "invokeai",
    "firefly",
    "flux",
    "dreamstudio",
]

METADATA_DISCLAIMER: str = (
    "Metadata extraction reflects embedded file container headers and EXIF fields. "
    "Metadata can be stripped by social media platforms, modified by benign post-processing, "
    "or intentionally fabricated. The presence or absence of metadata does not constitute "
    "definitive proof of authenticity or manipulation."
)


@dataclass
class ImageMetadataResult:
    """Structured result of image metadata inspection."""
    has_exif: bool = False
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    capture_time: Optional[str] = None
    software: Optional[str] = None
    orientation: Optional[int] = None
    orientation_description: Optional[str] = None
    identifiable_fields: List[str] = field(default_factory=list)
    raw_tags: Dict[str, Any] = field(default_factory=dict)
    noteworthy_markers: List[str] = field(default_factory=list)
    disclaimer: str = METADATA_DISCLAIMER
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


def _safe_str(val: Any) -> Optional[str]:
    """Clean and convert metadata value to a stripped string, handling byte encodings."""
    if val is None:
        return None
    if isinstance(val, bytes):
        try:
            val = val.decode("utf-8", errors="replace")
        except Exception:
            return None
    cleaned = str(val).strip("\x00 \t\r\n")
    return cleaned if cleaned else None


def _inspect_software_markers(
    software: Optional[str],
    other_fields: Dict[str, Any],
    markers: List[str]
) -> None:
    """Inspect software strings and container fields for noteworthy editing or generative markers."""
    all_inspectable_text: List[str] = []
    if software:
        all_inspectable_text.append(software)

    for field_name in ("UserComment", "ImageDescription", "parameters", "Comment", "prompt"):
        if field_name in other_fields:
            val = _safe_str(other_fields[field_name])
            if val:
                all_inspectable_text.append(val)

    combined_lower = " ".join(all_inspectable_text).lower()

    # Check for image editing signatures
    for kw in EDITING_SOFTWARE_KEYWORDS:
        if kw in combined_lower:
            markers.append(
                f"Metadata references digital editing software: '{kw.title()}'. "
                "This is a metadata finding; it indicates post-processing but does not prove fraudulent tampering."
            )
            break

    # Check for generative AI synthesis signatures
    for kw in GENERATIVE_TOOL_KEYWORDS:
        if kw in combined_lower:
            markers.append(
                f"Metadata references generative AI tooling or parameters: '{kw}'. "
                "This is an observational indicator; verify original context and origin."
            )
            break


def extract_image_metadata(image_input: Union[Image.Image, bytes, bytearray, io.BytesIO]) -> Dict[str, Any]:
    """
    Extract and analyze metadata from an image, safely handling missing or malformed headers.

    Args:
        image_input: Either an open PIL.Image.Image instance or raw image bytes.

    Returns:
        A dictionary representation of ImageMetadataResult conforming to T.R.A.C.E. conventions.
    """
    result = ImageMetadataResult()

    # Step 1: Resolve image instance safely
    img: Optional[Image.Image] = None
    should_close = False

    try:
        if isinstance(image_input, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image_input))
            should_close = True
        elif isinstance(image_input, io.BytesIO):
            img = Image.open(image_input)
            should_close = True
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            result.error = f"Unsupported image input type: {type(image_input).__name__}"
            result.noteworthy_markers.append("Unrecognized input format for metadata extraction.")
            return result.to_dict()

        raw_tags: Dict[str, Any] = {}
        identifiable_fields: List[str] = []

        # Step 2: Extract primary EXIF tags
        exif_data = None
        try:
            exif_data = img.getexif()
        except Exception as e:
            logger.warning("Error reading getexif(): %s", str(e))

        has_valid_exif = False
        if exif_data is not None and len(exif_data) > 0:
            for tag_id, val in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                clean_val = _safe_str(val)
                if clean_val is not None:
                    has_valid_exif = True
                    raw_tags[tag_name] = clean_val
                    identifiable_fields.append(tag_name)

            # Step 3: Extract Exif IFD sub-directory (DateTimeOriginal, LensModel, etc.)
            try:
                if hasattr(ExifTags, "IFD") and hasattr(ExifTags.IFD, "Exif"):
                    ifd_exif = exif_data.get_ifd(ExifTags.IFD.Exif)
                    for ifd_id, val in ifd_exif.items():
                        tag_name = ExifTags.TAGS.get(ifd_id, str(ifd_id))
                        clean_val = _safe_str(val)
                        if clean_val is not None and tag_name not in raw_tags:
                            has_valid_exif = True
                            raw_tags[tag_name] = clean_val
                            identifiable_fields.append(tag_name)
            except Exception as ifd_err:
                logger.debug("Optional Exif IFD extraction skipped: %s", str(ifd_err))

        # Step 4: Extract container-level info (PNG text chunks, TIFF metadata)
        if hasattr(img, "info") and isinstance(img.info, dict):
            for info_key, info_val in img.info.items():
                clean_val = _safe_str(info_val)
                if clean_val is not None and str(info_key) not in raw_tags:
                    # Ignore binary EXIF blob in info dictionary
                    if info_key == "exif" and isinstance(info_val, bytes):
                        continue
                    raw_tags[str(info_key)] = clean_val
                    identifiable_fields.append(str(info_key))

        result.has_exif = has_valid_exif
        result.raw_tags = raw_tags
        result.identifiable_fields = list(dict.fromkeys(identifiable_fields))

        # Step 5: Normalize specific known forensic properties
        result.camera_make = raw_tags.get("Make")
        result.camera_model = raw_tags.get("Model")
        result.lens_model = raw_tags.get("LensModel") or raw_tags.get("Lens")
        result.capture_time = (
            raw_tags.get("DateTimeOriginal")
            or raw_tags.get("DateTimeDigitized")
            or raw_tags.get("DateTime")
        )
        result.software = raw_tags.get("Software") or raw_tags.get("software")

        # Orientation normalization
        raw_orient = raw_tags.get("Orientation")
        if raw_orient is not None:
            try:
                orient_int = int(raw_orient)
                result.orientation = orient_int
                result.orientation_description = ORIENTATION_DESCRIPTIONS.get(
                    orient_int, f"Custom orientation value ({orient_int})"
                )
            except (ValueError, TypeError):
                result.orientation_description = str(raw_orient)

        # Step 6: Identify noteworthy forensic markers
        markers: List[str] = []

        if result.camera_make or result.camera_model:
            cam_str = f"{result.camera_make or ''} {result.camera_model or ''}".strip()
            markers.append(
                f"Camera hardware identifiers present: '{cam_str}'. "
                "Hardware headers indicate direct capture device provenance unless modified."
            )

        if not result.has_exif:
            markers.append(
                "No EXIF metadata found. This is standard for web exports and messaging platforms "
                "and does not establish that the media is synthetic or manipulated."
            )

        _inspect_software_markers(result.software, raw_tags, markers)

        result.noteworthy_markers = markers

    except (UnidentifiedImageError, OSError, ValueError) as err:
        logger.error("Failed to decode image during metadata extraction: %s", str(err))
        result.has_exif = False
        result.error = f"Image decode error: {type(err).__name__}"
        result.noteworthy_markers.append("Image data was malformed, corrupted, or unreadable.")
    except Exception as unexpected_err:
        logger.error("Unexpected error during metadata extraction: %s", str(unexpected_err))
        result.has_exif = False
        result.error = f"Metadata extraction failed: {str(unexpected_err)}"
        result.noteworthy_markers.append("Metadata extraction encountered an unexpected error.")
    finally:
        if should_close and img is not None:
            try:
                img.close()
            except Exception:
                pass

    return result.to_dict()
