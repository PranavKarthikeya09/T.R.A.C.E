"""Error Level Analysis (ELA) Forensic Anomaly Map Generator.

Provides deterministic, standalone forensic signal processing using native Pillow capabilities.
Generates spatial anomaly visualizations by computing per-pixel compression residuals
between an input image and an in-memory recompressed reference at a configurable quality.

METHODOLOGY & POLICIES:
1. Input Normalization & Transparency Policy:
   JPEG compression does not natively support transparency (alpha channels).
   If an input image contains transparency (modes RGBA, LA, or P with transparency),
   it is alpha-composited over a neutral opaque white matte (255, 255, 255) prior to comparison.
   Non-RGB images (e.g., Grayscale 'L', Palette 'P', 'CMYK') are converted to standard RGB.

2. In-Memory Recompression:
   The reference image is generated purely in memory via io.BytesIO at a configurable JPEG
   quality (default: 95). No temporary files are written to disk.

3. Residual Calculation:
   The per-pixel absolute difference between the normalized source and recompressed reference
   is computed across color channels (R, G, B). The single-channel spatial residual magnitude is
   derived as the maximum channel difference:
       Residual(x, y) = max(|R_orig - R_recomp|, |G_orig - G_recomp|, |B_orig - B_recomp|)
   This preserves chroma-specific compression discrepancies that standard luminance down-mixing
   would dilute.

4. Normalization Method & Limitations:
   Raw residual statistics (min, max, mean, std, rms) are preserved separately without scaling.
   For visualization, residuals are mapped via a 99th-percentile linear ceiling:
       - If max residual is 0 (uniform image), output is zero (no division-by-zero).
       - The 99th percentile (p99) of non-zero residuals is computed from the 256-bin histogram.
       - Residuals are scaled by (255.0 / effective_ceiling) where effective_ceiling = max(p99, max_residual).
       - Values exceeding the ceiling clamp to 255.
   Limitations: Extreme residual spikes saturate at 255. In pristine unedited images, tiny
   quantization steps (1-2 units) will be magnified; this reflects standard JPEG DCT block
   quantization, not tampering.

5. Thermal Colormap:
   Grayscale residuals are mapped to a 5-stop perceptual heatmap:
   Dark Indigo/Navy (0) -> Deep Blue (64) -> Cyan/Teal (128) -> Golden Yellow (192) -> Fiery Red (255).
   Zero-residual pixels render as dark navy/black.
"""
from dataclasses import dataclass, field, asdict
import base64
import io
import logging
import math
from typing import Any, Dict, List, Optional, Union
from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError

logger = logging.getLogger(__name__)

DEFAULT_JPEG_QUALITY: int = 95
DEFAULT_MAX_PIXELS: int = 25_000_000  # 25 megapixels safe processing limit
DEFAULT_MAX_VISUALIZATION_DIMENSION: int = 1280  # Max dimension for base64 PNG transmission

ELA_DISCLAIMER: str = (
    "Error Level Analysis (ELA) is a heuristic visualization technique that highlights compression "
    "residuals between an image and an in-memory recompressed reference. It does not produce a "
    "validated manipulation mask, probability, or tamper confidence score. Image high-frequency texture, "
    "prior compression history, resizing, color quantization, and standard post-processing can all produce "
    "pronounced residuals in authentic images. ELA visualizations should be evaluated as exploratory "
    "signals alongside other forensic evidence, not as standalone proof of manipulation."
)

ELA_LIMITATIONS: List[str] = [
    "Error Level Analysis is an exploratory heuristic visualization of JPEG compression differences, not a validated manipulation mask.",
    "Natural high-contrast edges and textures inherently exhibit higher compression residuals than uniform regions.",
    "Prior recompression history, downscaling, or social media re-encoding alters quantization grids and can obscure or introduce residuals.",
    "Downsampled visualization maps provide an exploratory overview and must not be used for pixel-level boundary localization.",
]


def _build_colormap_palette() -> List[int]:
    """Generate a 256-color (768 integers) perceptual thermal gradient palette."""
    anchors = [
        (0, (15, 15, 30)),       # Dark indigo / near black (baseline zero residual)
        (64, (20, 80, 180)),     # Deep blue (low residual / expected compression noise)
        (128, (20, 180, 140)),   # Cyan / teal (moderate residual)
        (192, (240, 200, 30)),   # Golden yellow (high residual)
        (255, (240, 40, 30)),    # Fiery red (peak residual)
    ]
    palette: List[int] = []
    for idx in range(256):
        for s in range(len(anchors) - 1):
            idx0, c0 = anchors[s]
            idx1, c1 = anchors[s + 1]
            if idx0 <= idx <= idx1:
                t = (idx - idx0) / (idx1 - idx0) if idx1 > idx0 else 0.0
                palette.extend([
                    round(c0[0] + t * (c1[0] - c0[0])),
                    round(c0[1] + t * (c1[1] - c0[1])),
                    round(c0[2] + t * (c1[2] - c0[2]))
                ])
                break
    return palette


COLORMAP_PALETTE: List[int] = _build_colormap_palette()


@dataclass
class ELAResult:
    """Structured result of Error Level Analysis (ELA) forensic anomaly map generation."""
    width: Optional[int] = None
    height: Optional[int] = None
    visualization_width: Optional[int] = None
    visualization_height: Optional[int] = None
    is_downsampled: bool = False
    map_type: str = "error_level_analysis"
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    scale_factor: float = 1.0
    normalization_method: str = "percentile_linear_p99"
    statistics: Dict[str, float] = field(default_factory=dict)
    heatmap_data_uri: Optional[str] = None
    grayscale_data_uri: Optional[str] = None
    limitations: List[str] = field(default_factory=lambda: list(ELA_LIMITATIONS))
    disclaimer: str = ELA_DISCLAIMER
    noteworthy_markers: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


def _prepare_rgb_image(img: Image.Image) -> Image.Image:
    """
    Prepare an image for ELA comparison by converting to RGB and handling transparency.

    Transparency Policy:
    If the image has an alpha channel (RGBA, LA) or palette transparency, it is composited
    over a neutral opaque white background (255, 255, 255). This prevents JPEG conversion
    crashes or black fringe artifacts.
    Other modes (e.g., Grayscale 'L', Palette 'P', 'CMYK') are converted directly to 'RGB'.
    """
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(background, rgba)
        return composited.convert("RGB")
    elif img.mode != "RGB":
        return img.convert("RGB")
    else:
        return img.copy()


def _image_to_png_data_uri(image: Image.Image) -> str:
    """Serialize a PIL Image into a base64-encoded PNG data URI."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def generate_ela_map(
    image_input: Union[Image.Image, bytes, bytearray, io.BytesIO],
    quality: int = DEFAULT_JPEG_QUALITY,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    max_visualization_dimension: Optional[int] = DEFAULT_MAX_VISUALIZATION_DIMENSION,
) -> Dict[str, Any]:
    """
    Generate an Error Level Analysis (ELA) anomaly visualization and residual statistics.

    Args:
        image_input: Either an open PIL.Image.Image instance or raw image bytes.
        quality: Configurable JPEG recompression quality setting (1 to 100, default 95).
        max_pixels: Safe maximum image pixel threshold to prevent excessive memory usage.
        max_visualization_dimension: Maximum dimension (width/height) for serialized visualization
            maps to limit HTTP payload size. If original image exceeds this, the visualization
            is safely downsampled while input dimensions and full-resolution statistics are preserved.

    Returns:
        A dictionary representation of ELAResult conforming to T.R.A.C.E. conventions.
    """
    result = ELAResult(jpeg_quality=quality)

    # Step 1: Validate configurable quality parameter
    if not isinstance(quality, int) or quality < 1 or quality > 100:
        result.error = f"Invalid JPEG quality '{quality}'. Quality must be an integer between 1 and 100."
        result.noteworthy_markers.append("Execution aborted due to invalid quality parameter.")
        return result.to_dict()

    # Step 2: Resolve image instance safely
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
            result.noteworthy_markers.append("Unrecognized input format for ELA processing.")
            return result.to_dict()

        orig_width, orig_height = img.size
        pixel_count = orig_width * orig_height
        result.width = orig_width
        result.height = orig_height

        # Step 3: Enforce large-image safety limit
        if pixel_count > max_pixels:
            result.error = (
                f"Image resolution ({orig_width}x{orig_height} = {pixel_count} pixels) "
                f"exceeds the maximum safe limit of {max_pixels} pixels."
            )
            result.noteworthy_markers.append("Processing aborted by large-image safety policy.")
            return result.to_dict()

        # Step 4: Normalize color representation and handle transparency
        rgb_source = _prepare_rgb_image(img)

        # Step 5: Generate in-memory recompressed JPEG reference
        recomp_buf = io.BytesIO()
        rgb_source.save(recomp_buf, format="JPEG", quality=quality)
        recomp_buf.seek(0)
        recompressed = Image.open(recomp_buf)
        recompressed.load()

        # Step 6: Compute per-pixel channel differences
        diff_rgb = ImageChops.difference(rgb_source, recompressed)
        r, g, b = diff_rgb.split()
        max_channel_residual = ImageChops.lighter(ImageChops.lighter(r, g), b)

        # Step 7: Calculate raw unscaled residual statistics
        stat = ImageStat.Stat(max_channel_residual)
        min_val = float(stat.extrema[0][0])
        max_val = float(stat.extrema[0][1])
        mean_val = float(stat.mean[0])
        std_val = float(stat.stddev[0])
        rms_val = float(stat.rms[0])

        # Compute 99th percentile residual via 256-bin histogram
        hist = max_channel_residual.histogram()
        total_pixels = pixel_count
        target_count = int(total_pixels * 0.99)
        cum_count = 0
        p99_val = 0.0
        for val, count in enumerate(hist):
            cum_count += count
            if cum_count >= target_count:
                p99_val = float(val)
                break

        # Populate well-defined, finite statistics
        result.statistics = {
            "min_residual": round(min_val, 4),
            "max_residual": round(max_val, 4),
            "mean_residual": round(mean_val, 4),
            "std_residual": round(std_val, 4),
            "rms_residual": round(rms_val, 4),
            "p99_residual": round(p99_val, 4),
        }

        # Step 8: Visualization Normalization
        # Prevent division-by-zero on zero-residual images
        if max_val == 0.0:
            result.scale_factor = 1.0
            normalized_gray = Image.new("L", (orig_width, orig_height), 0)
        else:
            # Saturation ceiling: use p99 to prevent extreme outliers from compressing the map
            ceiling = p99_val if p99_val > 0.0 else max_val
            scale = 255.0 / ceiling
            result.scale_factor = round(scale, 4)
            lut = [min(255, int(round(i * scale))) for i in range(256)]
            normalized_gray = max_channel_residual.point(lut)

        # Step 9: Enforce transmission payload size policy on visualization maps
        vis_gray = normalized_gray
        if max_visualization_dimension and max(orig_width, orig_height) > max_visualization_dimension:
            ratio = max_visualization_dimension / max(orig_width, orig_height)
            vis_w = max(1, int(round(orig_width * ratio)))
            vis_h = max(1, int(round(orig_height * ratio)))
            vis_gray = normalized_gray.resize((vis_w, vis_h), Image.Resampling.BILINEAR)
            result.visualization_width = vis_w
            result.visualization_height = vis_h
            result.is_downsampled = True
        else:
            result.visualization_width = orig_width
            result.visualization_height = orig_height
            result.is_downsampled = False

        # Step 10: Render colored heatmap via thermal palette
        heatmap_pal_img = vis_gray.copy()
        heatmap_pal_img.putpalette(COLORMAP_PALETTE)
        colored_heatmap = heatmap_pal_img.convert("RGB")

        # Step 11: Serialize outputs to base64 PNG data URIs
        result.grayscale_data_uri = _image_to_png_data_uri(vis_gray)
        result.heatmap_data_uri = _image_to_png_data_uri(colored_heatmap)

        # Step 12: Provide non-judgmental observational markers
        markers: List[str] = []
        if result.is_downsampled:
            markers.append(
                f"Visualization map downsampled from {orig_width}x{orig_height} to "
                f"{result.visualization_width}x{result.visualization_height} to limit response payload size. "
                "Downsampled maps are exploratory overviews and do not provide pixel-level localization."
            )
        if max_val == 0.0:
            markers.append(
                f"Image exhibited zero compression residual relative to reference at quality {quality}."
            )
        elif mean_val < 1.0:
            markers.append(
                f"Low mean residual ({mean_val:.2f}). Suggests high consistency with reference compression "
                "or predominantly flat, low-contrast content."
            )
        elif std_val > 5.0:
            markers.append(
                f"Elevated residual spatial variance (std: {std_val:.2f}). Non-uniform compression response "
                "observed; content complexity, high-contrast edges, or disparate compression histories may contribute."
            )
        else:
            markers.append(
                f"Moderate residual levels observed (mean: {mean_val:.2f}, max: {max_val:.2f})."
            )

        result.noteworthy_markers = markers

    except (UnidentifiedImageError, OSError, ValueError) as err:
        logger.error("Failed to decode image during ELA generation: %s", str(err))
        result.error = f"Image decode error: {type(err).__name__}"
        result.noteworthy_markers.append("Image data was malformed, corrupted, or unreadable.")
    except Exception as unexpected_err:
        logger.error("Unexpected error during ELA generation: %s", str(unexpected_err))
        result.error = f"ELA generation failed: {str(unexpected_err)}"
        result.noteworthy_markers.append("ELA generator encountered an unexpected error.")
    finally:
        if should_close and img is not None:
            try:
                img.close()
            except Exception:
                pass

    return result.to_dict()
