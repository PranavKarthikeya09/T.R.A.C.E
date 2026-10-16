"""Automated test suite for image metadata and EXIF forensic inspector.

Verifies:
1. Valid images with no EXIF headers.
2. Images with camera make, model, and lens metadata.
3. Images with editing software tags (e.g., Photoshop).
4. Images with generative AI tool parameters (e.g., Stable Diffusion, Midjourney).
5. Malformed, corrupted, or invalid bytes handling without raising exceptions.
6. Acceptance of both raw bytes and open PIL.Image.Image instances.
7. Consistent, documented output dictionary structure.
"""
import io
import pytest
from PIL import Image, ExifTags, PngImagePlugin

from app.forensics.metadata_parser import (
    extract_image_metadata,
    METADATA_DISCLAIMER,
    ORIENTATION_DESCRIPTIONS,
)


def _create_synthetic_jpeg_with_exif(exif_dict: dict, ifd_dict: dict = None) -> bytes:
    """Helper to construct a deterministic in-memory JPEG with custom EXIF tags."""
    img = Image.new("RGB", (64, 64), color="blue")
    exif = img.getexif()

    for tag_id, value in exif_dict.items():
        exif[tag_id] = value

    if ifd_dict and hasattr(ExifTags, "IFD") and hasattr(ExifTags.IFD, "Exif"):
        ifd = exif.get_ifd(ExifTags.IFD.Exif)
        for tag_id, value in ifd_dict.items():
            ifd[tag_id] = value

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _create_synthetic_png_with_info(text_chunks: dict) -> bytes:
    """Helper to construct a deterministic in-memory PNG with text metadata chunks."""
    img = Image.new("RGB", (64, 64), color="green")
    pnginfo = PngImagePlugin.PngInfo()
    for k, v in text_chunks.items():
        pnginfo.add_text(k, v)

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=pnginfo)
    return buf.getvalue()


class TestMetadataInspector:
    """Test suite for standalone metadata extraction module."""

    def test_valid_image_with_no_exif(self):
        """Test that pristine image with zero EXIF returns clean structure and appropriate flags."""
        img = Image.new("RGB", (32, 32), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        # Test with raw bytes
        result = extract_image_metadata(raw_bytes)

        assert isinstance(result, dict)
        assert result["has_exif"] is False
        assert result["camera_make"] is None
        assert result["camera_model"] is None
        assert result["lens_model"] is None
        assert result["capture_time"] is None
        assert result["software"] is None
        assert result["orientation"] is None
        assert result["error"] is None
        assert result["disclaimer"] == METADATA_DISCLAIMER
        assert any("no exif metadata found" in m.lower() for m in result["noteworthy_markers"])

        # Test with open PIL Image instance
        img_open = Image.open(io.BytesIO(raw_bytes))
        result_img = extract_image_metadata(img_open)
        assert result_img["has_exif"] is False
        assert result_img["error"] is None

    def test_image_with_camera_metadata(self):
        """Test extraction of camera make, model, lens, timestamp, and orientation."""
        # 271: Make, 272: Model, 274: Orientation, 306: DateTime
        exif_tags = {
            271: "Sony",
            272: "ILCE-7RM4",
            274: 1,
            306: "2024:06:15 10:22:45",
        }
        # 36867: DateTimeOriginal, 42036: LensModel
        ifd_tags = {
            36867: "2024:06:15 10:22:45",
            42036: "FE 24-70mm F2.8 GM II",
        }

        jpeg_bytes = _create_synthetic_jpeg_with_exif(exif_tags, ifd_tags)
        result = extract_image_metadata(jpeg_bytes)

        assert result["has_exif"] is True
        assert result["camera_make"] == "Sony"
        assert result["camera_model"] == "ILCE-7RM4"
        assert result["lens_model"] == "FE 24-70mm F2.8 GM II"
        assert result["capture_time"] == "2024:06:15 10:22:45"
        assert result["orientation"] == 1
        assert result["orientation_description"] == ORIENTATION_DESCRIPTIONS[1]
        assert "Make" in result["identifiable_fields"]
        assert "Model" in result["identifiable_fields"]
        assert any("camera hardware identifiers present" in m.lower() for m in result["noteworthy_markers"])

    def test_image_with_editing_software_tag(self):
        """Test detection and non-judgmental flagging of digital image editing software."""
        # 305: Software tag
        exif_tags = {
            305: "Adobe Photoshop 25.4 (Macintosh)",
            271: "Nikon",
            272: "D850",
        }
        jpeg_bytes = _create_synthetic_jpeg_with_exif(exif_tags)
        result = extract_image_metadata(jpeg_bytes)

        assert result["has_exif"] is True
        assert result["software"] == "Adobe Photoshop 25.4 (Macintosh)"
        assert result["camera_make"] == "Nikon"

        # Verify editing software marker is present and carefully framed
        editing_markers = [m for m in result["noteworthy_markers"] if "digital editing software" in m.lower()]
        assert len(editing_markers) == 1
        assert "photoshop" in editing_markers[0].lower()
        # Verify it explicitly communicates uncertainty
        assert "does not prove fraudulent tampering" in editing_markers[0].lower()

    def test_generative_ai_markers_in_png_info(self):
        """Test that generative AI traces in container metadata are identified."""
        png_bytes = _create_synthetic_png_with_info({
            "Software": "Stable Diffusion web UI",
            "parameters": "photorealistic portrait, steps: 25, sampler: Euler a",
        })

        result = extract_image_metadata(png_bytes)

        assert result["software"] == "Stable Diffusion web UI"
        assert "parameters" in result["raw_tags"]
        ai_markers = [m for m in result["noteworthy_markers"] if "generative ai tooling" in m.lower()]
        assert len(ai_markers) >= 1
        assert "stable diffusion" in ai_markers[0].lower()
        assert "observational indicator" in ai_markers[0].lower()

    def test_malformed_bytes_handled_safely(self):
        """Test that corrupt or unreadable image bytes do not raise exceptions."""
        corrupt_bytes = b"NOT_A_VALID_IMAGE_HEADER_BYTES_RANDOM"
        result = extract_image_metadata(corrupt_bytes)

        assert isinstance(result, dict)
        assert result["has_exif"] is False
        assert result["error"] is not None
        assert "image decode error" in result["error"].lower()
        assert any("malformed, corrupted, or unreadable" in m.lower() for m in result["noteworthy_markers"])

    def test_empty_bytes_handled_safely(self):
        """Test that empty bytes do not raise exceptions."""
        result = extract_image_metadata(b"")

        assert isinstance(result, dict)
        assert result["has_exif"] is False
        assert result["error"] is not None

    def test_invalid_type_input_handled_safely(self):
        """Test that passing invalid types (e.g., None, integer) returns an error result."""
        result = extract_image_metadata(None)

        assert isinstance(result, dict)
        assert result["has_exif"] is False
        assert "unsupported image input type" in result["error"].lower()

    def test_consistent_output_schema_keys(self):
        """Verify that output dictionary always contains all documented keys."""
        required_keys = {
            "has_exif",
            "camera_make",
            "camera_model",
            "lens_model",
            "capture_time",
            "software",
            "orientation",
            "orientation_description",
            "identifiable_fields",
            "raw_tags",
            "noteworthy_markers",
            "disclaimer",
            "error",
        }

        img = Image.new("RGB", (10, 10))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = extract_image_metadata(buf.getvalue())

        assert required_keys.issubset(set(result.keys()))
