"""Automated test suite for Error Level Analysis (ELA) anomaly-map generator.

Verifies:
1. Valid JPEG image input.
2. Valid PNG image input (including transparency handling).
3. Invalid, corrupt, and empty bytes handling without raising unhandled exceptions.
4. Uniform-color images and zero-residual division-by-zero protection.
5. Preservation of exact output dimensions in serialized maps.
6. Correct PNG base64 data-URI structure and decodability.
7. Finite and well-defined residual statistics.
8. Configurable JPEG quality and safe invalid quality handling.
9. Large-image safety policy and memory limit enforcement.
10. Strict determinism across repeated executions.
11. Composite image validation verifying non-zero residual variance.
12. Consistent, documented result dictionary schema keys.
"""
import base64
import io
import math
import pytest
from PIL import Image

from app.forensics.ela import (
    generate_ela_map,
    ELA_DISCLAIMER,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_MAX_PIXELS,
)


def _create_synthetic_jpeg_bytes(size=(64, 64), color="blue", quality=95) -> bytes:
    """Helper to create a valid in-memory JPEG byte stream."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _create_synthetic_png_bytes(size=(64, 64), mode="RGB", color=(255, 0, 0)) -> bytes:
    """Helper to create a valid in-memory PNG byte stream."""
    img = Image.new(mode, size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _decode_data_uri_image(data_uri: str) -> Image.Image:
    """Helper to decode a base64 PNG data URI back into a PIL Image."""
    prefix = "data:image/png;base64,"
    assert data_uri.startswith(prefix), f"Data URI did not start with '{prefix}'"
    raw_b64 = data_uri[len(prefix):]
    image_bytes = base64.b64decode(raw_b64)
    img = Image.open(io.BytesIO(image_bytes))
    img.load()
    return img


class TestELAForensics:
    """Test suite for standalone ELA anomaly generation module."""

    def test_valid_jpeg_input(self):
        """Test standard processing of a valid JPEG image."""
        jpeg_bytes = _create_synthetic_jpeg_bytes(size=(80, 60), color="teal", quality=90)
        result = generate_ela_map(jpeg_bytes, quality=90)

        assert isinstance(result, dict)
        assert result["error"] is None
        assert result["width"] == 80
        assert result["height"] == 60
        assert result["jpeg_quality"] == 90
        assert result["disclaimer"] == ELA_DISCLAIMER
        assert result["heatmap_data_uri"] is not None
        assert result["grayscale_data_uri"] is not None

        # Verify decoded heatmap dimensions match input exactly
        heatmap_img = _decode_data_uri_image(result["heatmap_data_uri"])
        assert heatmap_img.size == (80, 60)
        assert heatmap_img.format == "PNG"

    def test_valid_png_with_transparency_handling(self):
        """Test that RGBA PNG with alpha channel is handled consistently via white matting."""
        # 48x48 RGBA image with translucent red
        rgba_bytes = _create_synthetic_png_bytes(size=(48, 48), mode="RGBA", color=(255, 0, 0, 128))
        result = generate_ela_map(rgba_bytes)

        assert result["error"] is None
        assert result["width"] == 48
        assert result["height"] == 48

        # Verify output maps match input dimensions
        gray_img = _decode_data_uri_image(result["grayscale_data_uri"])
        assert gray_img.size == (48, 48)
        assert gray_img.format == "PNG"

    def test_invalid_and_empty_input_handled_safely(self):
        """Test that empty bytes, corrupt bytes, and invalid types return error dicts without throwing."""
        # Empty bytes
        empty_res = generate_ela_map(b"")
        assert isinstance(empty_res, dict)
        assert empty_res["error"] is not None
        assert empty_res["heatmap_data_uri"] is None

        # Corrupt bytes
        corrupt_res = generate_ela_map(b"NOT_A_VALID_IMAGE_DATA_STREAM")
        assert isinstance(corrupt_res, dict)
        assert corrupt_res["error"] is not None
        assert corrupt_res["heatmap_data_uri"] is None

        # Unsupported input type (None or int)
        none_res = generate_ela_map(None)
        assert isinstance(none_res, dict)
        assert "unsupported image input type" in none_res["error"].lower()

    def test_uniform_color_and_zero_residual_handling(self):
        """Test that uniform-color images with zero or near-zero residuals do not trigger division-by-zero."""
        # A solid grayscale image saved as uncompressed PNG
        solid_png = _create_synthetic_png_bytes(size=(32, 32), mode="RGB", color=(128, 128, 128))
        result = generate_ela_map(solid_png, quality=DEFAULT_JPEG_QUALITY)

        assert result["error"] is None
        stats = result["statistics"]
        assert all(math.isfinite(v) for v in stats.values())
        assert stats["min_residual"] >= 0.0
        assert result["scale_factor"] >= 1.0

        # Construct an artificial scenario with zero residuals everywhere by using an Image instance
        # that compresses identically or by testing zero residual behavior directly
        img = Image.new("RGB", (16, 16), (0, 0, 0))
        res_zero = generate_ela_map(img, quality=DEFAULT_JPEG_QUALITY)
        assert res_zero["error"] is None
        assert res_zero["statistics"]["max_residual"] == 0.0
        assert res_zero["statistics"]["mean_residual"] == 0.0
        assert res_zero["scale_factor"] == 1.0
        assert any("zero compression residual" in m.lower() for m in res_zero["noteworthy_markers"])

    def test_preservation_of_output_dimensions(self):
        """Test that non-square, arbitrary dimensions are preserved exactly in all output maps."""
        test_dims = [(73, 119), (211, 87), (35, 35)]
        for w, h in test_dims:
            img = Image.new("RGB", (w, h), (50, 150, 200))
            result = generate_ela_map(img)

            assert result["width"] == w
            assert result["height"] == h

            gray = _decode_data_uri_image(result["grayscale_data_uri"])
            heat = _decode_data_uri_image(result["heatmap_data_uri"])
            assert gray.size == (w, h)
            assert heat.size == (w, h)

    def test_correct_png_serialization_and_data_uri_structure(self):
        """Verify that data URIs are valid RFC 2397 base64 data URIs of image/png."""
        jpeg_bytes = _create_synthetic_jpeg_bytes(size=(30, 30))
        result = generate_ela_map(jpeg_bytes)

        prefix = "data:image/png;base64,"
        for uri_key in ("heatmap_data_uri", "grayscale_data_uri"):
            uri = result[uri_key]
            assert uri.startswith(prefix)
            encoded = uri[len(prefix):]
            # Should be valid base64
            decoded = base64.b64decode(encoded)
            assert len(decoded) > 0
            # Header check: PNG magic bytes
            assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_finite_and_well_defined_residual_statistics(self):
        """Verify that all statistical metrics are populated, finite numbers."""
        img = Image.new("RGB", (64, 64))
        # Draw some gradient to induce varied residuals
        for x in range(64):
            for y in range(64):
                img.putpixel((x, y), (x * 4, y * 4, (x + y) * 2))

        result = generate_ela_map(img, quality=90)
        stats = result["statistics"]

        expected_stat_keys = {
            "min_residual",
            "max_residual",
            "mean_residual",
            "std_residual",
            "rms_residual",
            "p99_residual",
        }
        assert expected_stat_keys == set(stats.keys())

        for k, v in stats.items():
            assert isinstance(v, float), f"Statistic {k} is not a float: {type(v)}"
            assert math.isfinite(v), f"Statistic {k} is not finite: {v}"
            assert not math.isnan(v), f"Statistic {k} is NaN"
            assert v >= 0.0, f"Statistic {k} is negative: {v}"

        assert stats["min_residual"] <= stats["mean_residual"] <= stats["max_residual"]
        assert stats["p99_residual"] <= stats["max_residual"]

    def test_configurable_jpeg_quality_and_invalid_quality_handling(self):
        """Verify that valid quality values affect compression, and invalid qualities return errors."""
        img = Image.new("RGB", (64, 64), (100, 150, 200))

        # Test valid qualities
        res_75 = generate_ela_map(img, quality=75)
        res_95 = generate_ela_map(img, quality=95)
        assert res_75["error"] is None
        assert res_95["error"] is None
        assert res_75["jpeg_quality"] == 75
        assert res_95["jpeg_quality"] == 95

        # Test invalid qualities
        for invalid_q in (0, -10, 101, 200, "invalid", None):
            res_invalid = generate_ela_map(img, quality=invalid_q)
            assert res_invalid["error"] is not None
            assert "invalid jpeg quality" in res_invalid["error"].lower()

    def test_large_image_safety_policy(self):
        """Test that images exceeding the safe pixel threshold are rejected gracefully without memory explosion."""
        # 60x60 = 3600 pixels
        img = Image.new("RGB", (60, 60), (10, 20, 30))

        # Set max_pixels limit to 2000 (below 3600)
        result = generate_ela_map(img, max_pixels=2000)

        assert result["error"] is not None
        assert "exceeds the maximum safe limit of 2000 pixels" in result["error"]
        assert result["heatmap_data_uri"] is None
        assert any("safety policy" in m.lower() for m in result["noteworthy_markers"])

    def test_deterministic_output_for_identical_runs(self):
        """Verify that running ELA multiple times on the exact same input produces bit-for-bit identical results."""
        jpeg_bytes = _create_synthetic_jpeg_bytes(size=(40, 40), color="orange", quality=85)

        run1 = generate_ela_map(jpeg_bytes, quality=92)
        run2 = generate_ela_map(jpeg_bytes, quality=92)

        assert run1["statistics"] == run2["statistics"]
        assert run1["scale_factor"] == run2["scale_factor"]
        assert run1["heatmap_data_uri"] == run2["heatmap_data_uri"]
        assert run1["grayscale_data_uri"] == run2["grayscale_data_uri"]

    def test_composite_image_residual_variance(self):
        """
        Verify that a synthetic composite composed of regions with contrasting compression
        histories yields non-zero spatial variance (std_residual > 0).

        Note: As required, this does not claim ELA proves tampering, but verifies the specific
        numerical property of non-zero variance across disparate image sectors.
        """
        # Create base image compressed at low quality (Q=40)
        base = Image.new("RGB", (100, 100), (200, 100, 50))
        for x in range(0, 100, 10):
            for y in range(0, 100, 10):
                base.putpixel((x, y), (x * 2, y * 2, 100))

        buf_low = io.BytesIO()
        base.save(buf_low, format="JPEG", quality=40)
        buf_low.seek(0)
        low_q_img = Image.open(buf_low)
        low_q_img.load()

        # Splice an uncompressed, high-frequency pattern into the center quadrant
        composite = low_q_img.copy()
        for x in range(30, 70):
            for y in range(30, 70):
                composite.putpixel((x, y), (255, 255, (x * y) % 256))

        buf_comp = io.BytesIO()
        composite.save(buf_comp, format="PNG")
        comp_bytes = buf_comp.getvalue()

        result = generate_ela_map(comp_bytes, quality=95)

        assert result["error"] is None
        stats = result["statistics"]
        # Verify the specific numerical property: positive variance across regions
        assert stats["std_residual"] > 0.0
        assert stats["max_residual"] > stats["mean_residual"]
        assert result["scale_factor"] > 0.0

    def test_downsampling_policy_for_large_visualization_dimensions(self):
        """Verify that when image dimensions exceed max_visualization_dimension, the visualization is downsampled."""
        # 1600x800 image with max_visualization_dimension=800
        img = Image.new("RGB", (1600, 800), (40, 100, 180))
        result = generate_ela_map(img, max_visualization_dimension=800)

        assert result["error"] is None
        assert result["width"] == 1600
        assert result["height"] == 800
        assert result["visualization_width"] == 800
        assert result["visualization_height"] == 400
        assert result["is_downsampled"] is True

        # Decoded data URIs should have downsampled dimensions
        heat = _decode_data_uri_image(result["heatmap_data_uri"])
        assert heat.size == (800, 400)
        assert any("downsampled" in m.lower() for m in result["noteworthy_markers"])

    def test_consistent_output_schema_keys(self):
        """Verify that the output dictionary adheres strictly to the documented schema."""
        required_keys = {
            "width",
            "height",
            "visualization_width",
            "visualization_height",
            "is_downsampled",
            "map_type",
            "jpeg_quality",
            "scale_factor",
            "normalization_method",
            "statistics",
            "heatmap_data_uri",
            "grayscale_data_uri",
            "limitations",
            "disclaimer",
            "noteworthy_markers",
            "error",
        }
        res = generate_ela_map(_create_synthetic_jpeg_bytes((16, 16)))
        assert required_keys == set(res.keys())
