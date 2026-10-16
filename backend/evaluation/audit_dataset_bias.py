"""T.R.A.C.E. — Phase 17: Dataset Bias Audit.

Inspects actual image properties across both the 20-image baseline dataset
and the 40-image pilot dataset to quantify measurable dataset characteristics
(container format, resolution, aspect ratio, color mode, file size, metadata,
and semantic distribution) that could introduce classification shortcuts.
"""

import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from PIL import Image


def compute_sha256(filepath: str) -> str:
    """Calculates SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def canonical_aspect_ratio(w: int, h: int) -> str:
    d = gcd(w, h)
    # Simplify large ratios if not standard
    rw, rh = w // d, h // d
    if rw > 100 or rh > 100:
        val = w / h
        if abs(val - 1.0) < 0.02:
            return "1:1"
        if abs(val - 1.5) < 0.05:
            return "3:2"
        if abs(val - (2/3)) < 0.05:
            return "2:3"
        if abs(val - (4/3)) < 0.05:
            return "4:3"
        if abs(val - (3/4)) < 0.05:
            return "3:4"
        if abs(val - (16/9)) < 0.05:
            return "16:9"
        return f"{val:.2f}:1"
    return f"{rw}:{rh}"


def chi_square_2x2(table: List[List[int]]) -> Tuple[float, float]:
    """Computes Pearson's Chi-square statistic and approximate p-value for a 2x2 table."""
    # table = [[a, b], [c, d]]
    a, b = table[0]
    c, d = table[1]
    n = a + b + c + d
    if n == 0:
        return 0.0, 1.0
    r1, r2 = a + b, c + d
    c1, c2 = a + c, b + d
    if r1 == 0 or r2 == 0 or c1 == 0 or c2 == 0:
        return 0.0, 1.0

    # Expected counts
    e11 = r1 * c1 / n
    e12 = r1 * c2 / n
    e21 = r2 * c1 / n
    e22 = r2 * c2 / n

    chi2 = ((a - e11)**2 / e11) + ((b - e12)**2 / e12) + ((c - e21)**2 / e21) + ((d - e22)**2 / e22)
    # 1 df p-value approximation via survival function of chi2: exp(-chi2/2) * sqrt(2/pi) approx or upper bound
    # Using incomplete gamma / standard 1-df chi2 approximation:
    # p = erfc(sqrt(chi2 / 2))
    p_val = math.erfc(math.sqrt(max(0.0, chi2) / 2.0))
    return float(chi2), float(p_val)


def mutual_information_binary(x: List[int], y: List[int]) -> float:
    """Computes discrete mutual information I(X; Y) in bits."""
    n = len(x)
    if n == 0:
        return 0.0
    joint = Counter(zip(x, y))
    p_x = Counter(x)
    p_y = Counter(y)

    mi = 0.0
    for (xi, yi), count in joint.items():
        p_xy = count / n
        px = p_x[xi] / n
        py = p_y[yi] / n
        if p_xy > 0 and px > 0 and py > 0:
            mi += p_xy * math.log2(p_xy / (px * py))
    return max(0.0, mi)


def audit_dataset(manifest_path: str, repo_root: str) -> Dict[str, Any]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    samples = manifest.get("samples", [])
    records = []

    for s in samples:
        rel_path = s["image_path"]
        abs_path = os.path.normpath(os.path.join(repo_root, rel_path))
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Missing file: {abs_path}")

        file_size = os.path.getsize(abs_path)
        sha256_hash = compute_sha256(abs_path)
        ext = os.path.splitext(abs_path)[1].lower().lstrip(".")

        with Image.open(abs_path) as img:
            detected_format = (img.format or "UNKNOWN").upper()
            color_mode = img.mode
            channels = len(img.getbands())
            bands = list(img.getbands())
            w, h = img.size
            pixel_count = w * h
            aspect_ratio_num = round(w / h, 4)
            aspect_ratio_str = canonical_aspect_ratio(w, h)

            # Check metadata
            info_keys = list(img.info.keys())
            has_exif = bool(img.getexif()) or ("exif" in img.info)
            has_png_text = any(k in ["parameters", "Comment", "Description", "Software"] for k in info_keys)

        rec = {
            "id": s["id"],
            "image_path": rel_path,
            "ground_truth": s["ground_truth"],  # 0 = authentic, 1 = synthetic
            "class_label": "synthetic" if s["ground_truth"] == 1 else "authentic",
            "file_ext": ext,
            "detected_format": detected_format,
            "color_mode": color_mode,
            "channels": channels,
            "bands": bands,
            "width": w,
            "height": h,
            "total_pixels": pixel_count,
            "aspect_ratio_num": aspect_ratio_num,
            "aspect_ratio_str": aspect_ratio_str,
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "sha256": sha256_hash,
            "sha256_matches_manifest": sha256_hash == s.get("sha256"),
            "metadata_keys": info_keys,
            "has_exif": has_exif,
            "has_generative_metadata": has_png_text,
            "source_dataset": s.get("source_dataset", "unknown"),
            "generator_family": s.get("generator_family", s.get("generator_type", "unknown")),
            "semantic_category": s.get("semantic_category", "unspecified"),
            "split": s.get("split", "n/a"),
            "is_held_out": s.get("is_held_out", False),
        }
        records.append(rec)

    # Compute comparative statistics
    auth = [r for r in records if r["ground_truth"] == 0]
    synth = [r for r in records if r["ground_truth"] == 1]

    def summarize_numeric(values: List[float]) -> Dict[str, float]:
        if not values:
            return {}
        s = sorted(values)
        mean = sum(s) / len(s)
        var = sum((x - mean)**2 for x in s) / len(s)
        med = s[len(s) // 2] if len(s) % 2 != 0 else (s[len(s)//2 - 1] + s[len(s)//2]) / 2.0
        return {
            "mean": round(mean, 2),
            "std": round(math.sqrt(var), 2),
            "median": round(med, 2),
            "min": round(min(s), 2),
            "max": round(max(s), 2),
        }

    # Format distribution
    auth_formats = Counter(r["detected_format"] for r in auth)
    synth_formats = Counter(r["detected_format"] for r in synth)

    # Color mode distribution
    auth_modes = Counter(r["color_mode"] for r in auth)
    synth_modes = Counter(r["color_mode"] for r in synth)

    # Aspect ratio categories: Square (1:1), Landscape (>1.0), Portrait (<1.0)
    def categorize_ar(r: float) -> str:
        if abs(r - 1.0) < 0.02:
            return "Square (1:1)"
        return "Landscape" if r > 1.0 else "Portrait"

    auth_ar_cat = Counter(categorize_ar(r["aspect_ratio_num"]) for r in auth)
    synth_ar_cat = Counter(categorize_ar(r["aspect_ratio_num"]) for r in synth)

    # Resolutions
    auth_res = Counter(f"{r['width']}x{r['height']}" for r in auth)
    synth_res = Counter(f"{r['width']}x{r['height']}" for r in synth)

    # Semantic categories
    auth_semantics = Counter(r["semantic_category"] for r in auth)
    synth_semantics = Counter(r["semantic_category"] for r in synth)

    # Metadata presence
    auth_exif_count = sum(1 for r in auth if r["has_exif"])
    synth_exif_count = sum(1 for r in synth if r["has_exif"])
    auth_gen_meta_count = sum(1 for r in auth if r["has_generative_metadata"])
    synth_gen_meta_count = sum(1 for r in synth if r["has_generative_metadata"])

    # Contingency table: Format (PNG vs non-PNG) by Class (Auth vs Synth)
    # [ [auth_png, auth_non_png], [synth_png, synth_non_png] ]
    auth_png = sum(1 for r in auth if r["detected_format"] == "PNG")
    auth_non_png = len(auth) - auth_png
    synth_png = sum(1 for r in synth if r["detected_format"] == "PNG")
    synth_non_png = len(synth) - synth_png
    format_contingency = [[auth_png, auth_non_png], [synth_png, synth_non_png]]
    format_chi2, format_p = chi_square_2x2(format_contingency)

    # Contingency table: Square (1:1) vs Non-Square
    auth_sq = sum(1 for r in auth if abs(r["aspect_ratio_num"] - 1.0) < 0.02)
    auth_non_sq = len(auth) - auth_sq
    synth_sq = sum(1 for r in synth if abs(r["aspect_ratio_num"] - 1.0) < 0.02)
    synth_non_sq = len(synth) - synth_sq
    ar_contingency = [[auth_sq, auth_non_sq], [synth_sq, synth_non_sq]]
    ar_chi2, ar_p = chi_square_2x2(ar_contingency)

    # Mutual information
    # Format (binary: 1 if PNG else 0) vs Label
    labels = [r["ground_truth"] for r in records]
    format_bins = [1 if r["detected_format"] == "PNG" else 0 for r in records]
    mi_format_label = mutual_information_binary(format_bins, labels)

    # Aspect ratio (binary: 1 if Square else 0) vs Label
    sq_bins = [1 if abs(r["aspect_ratio_num"] - 1.0) < 0.02 else 0 for r in records]
    mi_sq_label = mutual_information_binary(sq_bins, labels)

    # High resolution (> 500k pixels) vs Label
    hires_bins = [1 if r["total_pixels"] >= 500000 else 0 for r in records]
    mi_hires_label = mutual_information_binary(hires_bins, labels)

    report = {
        "manifest_path": manifest_path,
        "sample_count": len(records),
        "class_breakdown": {
            "authentic": len(auth),
            "synthetic": len(synth),
        },
        "all_sha256_match_manifest": all(r["sha256_matches_manifest"] for r in records),
        "format_distribution": {
            "authentic": dict(auth_formats),
            "synthetic": dict(synth_formats),
        },
        "color_mode_distribution": {
            "authentic": dict(auth_modes),
            "synthetic": dict(synth_modes),
        },
        "aspect_ratio_category_distribution": {
            "authentic": dict(auth_ar_cat),
            "synthetic": dict(synth_ar_cat),
        },
        "resolution_distribution": {
            "authentic": dict(auth_res),
            "synthetic": dict(synth_res),
        },
        "total_pixels_summary": {
            "authentic": summarize_numeric([r["total_pixels"] for r in auth]),
            "synthetic": summarize_numeric([r["total_pixels"] for r in synth]),
        },
        "file_size_kb_summary": {
            "authentic": summarize_numeric([r["file_size_kb"] for r in auth]),
            "synthetic": summarize_numeric([r["file_size_kb"] for r in synth]),
        },
        "metadata_presence": {
            "authentic": {
                "exif_count": auth_exif_count,
                "exif_percent": round((auth_exif_count / len(auth)) * 100, 1) if auth else 0,
                "generative_chunks": auth_gen_meta_count,
            },
            "synthetic": {
                "exif_count": synth_exif_count,
                "exif_percent": round((synth_exif_count / len(synth)) * 100, 1) if synth else 0,
                "generative_chunks": synth_gen_meta_count,
            },
        },
        "statistical_association_tests": {
            "format_png_vs_non_png": {
                "contingency_table": format_contingency,
                "chi_square_statistic": round(format_chi2, 4),
                "approx_p_value": round(format_p, 4),
                "mutual_information_bits": round(mi_format_label, 4),
                "is_conflated": mi_format_label > 0.1,
            },
            "aspect_ratio_square_vs_rect": {
                "contingency_table": ar_contingency,
                "chi_square_statistic": round(ar_chi2, 4),
                "approx_p_value": round(ar_p, 4),
                "mutual_information_bits": round(mi_sq_label, 4),
                "is_conflated": mi_sq_label > 0.1,
            },
            "resolution_tier_hires_vs_standard": {
                "mutual_information_bits": round(mi_hires_label, 4),
                "is_conflated": mi_hires_label > 0.1,
            },
        },
        "sample_size_discussion": {
            "sample_size_per_class": len(auth),
            "total_samples": len(records),
            "is_statistically_sufficient": False,
            "limitation": (
                f"N={len(records)} ({len(auth)} authentic, {len(synth)} synthetic) is sufficient for a "
                "feasibility audit and qualitative bias identification, but insufficient to establish statistical "
                "generalization (e.g. margin of error at 95% confidence is ~15-20% on binary metrics)."
            ),
        },
        "records": records,
    }
    return report


def print_audit_summary(report: Dict[str, Any], title: str):
    print("=" * 80)
    print(f"T.R.A.C.E. — Phase 17: {title}")
    print("=" * 80)
    print(f"  Manifest:                {report['manifest_path']}")
    print(f"  Total Samples:           {report['sample_count']} ({report['class_breakdown']['authentic']} auth / {report['class_breakdown']['synthetic']} synth)")
    print(f"  SHA-256 Hashes Verified: {report['all_sha256_match_manifest']}")
    print("-" * 80)
    print("1. ENCODING FORMAT DISTRIBUTION:")
    print(f"   Authentic: {report['format_distribution']['authentic']}")
    print(f"   Synthetic: {report['format_distribution']['synthetic']}")
    chi_fmt = report['statistical_association_tests']['format_png_vs_non_png']
    print(f"   --> Association: Chi2={chi_fmt['chi_square_statistic']}, p={chi_fmt['approx_p_value']}, MI={chi_fmt['mutual_information_bits']} bits (Conflated: {chi_fmt['is_conflated']})")

    print("\n2. COLOR MODE DISTRIBUTION:")
    print(f"   Authentic: {report['color_mode_distribution']['authentic']}")
    print(f"   Synthetic: {report['color_mode_distribution']['synthetic']}")

    print("\n3. ASPECT RATIO DISTRIBUTION:")
    print(f"   Authentic: {report['aspect_ratio_category_distribution']['authentic']}")
    print(f"   Synthetic: {report['aspect_ratio_category_distribution']['synthetic']}")
    chi_ar = report['statistical_association_tests']['aspect_ratio_square_vs_rect']
    print(f"   --> Association: Chi2={chi_ar['chi_square_statistic']}, p={chi_ar['approx_p_value']}, MI={chi_ar['mutual_information_bits']} bits (Conflated: {chi_ar['is_conflated']})")

    print("\n4. RESOLUTION & PIXEL COUNT STATS:")
    auth_pix = report['total_pixels_summary']['authentic']
    synth_pix = report['total_pixels_summary']['synthetic']
    print(f"   Authentic Pixels: Mean={auth_pix.get('mean')}, Min={auth_pix.get('min')}, Max={auth_pix.get('max')}")
    print(f"   Synthetic Pixels: Mean={synth_pix.get('mean')}, Min={synth_pix.get('min')}, Max={synth_pix.get('max')}")

    print("\n5. FILE SIZE STATS (KB):")
    auth_sz = report['file_size_kb_summary']['authentic']
    synth_sz = report['file_size_kb_summary']['synthetic']
    print(f"   Authentic Size: Mean={auth_sz.get('mean')} KB, Median={auth_sz.get('median')} KB, Max={auth_sz.get('max')} KB")
    print(f"   Synthetic Size: Mean={synth_sz.get('mean')} KB, Median={synth_sz.get('median')} KB, Max={synth_sz.get('max')} KB")

    print("\n6. METADATA & HEADERS:")
    print(f"   Authentic: EXIF present in {report['metadata_presence']['authentic']['exif_count']} ({report['metadata_presence']['authentic']['exif_percent']}%)")
    print(f"   Synthetic: EXIF present in {report['metadata_presence']['synthetic']['exif_count']} ({report['metadata_presence']['synthetic']['exif_percent']}%), Gen Chunks: {report['metadata_presence']['synthetic']['generative_chunks']}")

    print("\n7. STATISTICAL POWER & LIMITATION:")
    print(f"   {report['sample_size_discussion']['limitation']}")
    print("=" * 80)


def main():
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
    os.makedirs(cache_dir, exist_ok=True)

    pilot_manifest = os.path.join(os.path.dirname(__file__), "pilot_manifest.json")
    baseline_manifest = os.path.join(os.path.dirname(__file__), "dataset_manifest.json")

    print("Executing Dataset Bias Audit across Pilot and Baseline datasets...\n")

    pilot_report = audit_dataset(pilot_manifest, repo_root)
    print_audit_summary(pilot_report, "PILOT DATASET (40 SAMPLES) BIAS AUDIT")

    baseline_report = audit_dataset(baseline_manifest, repo_root)
    print_audit_summary(baseline_report, "BASELINE DATASET (20 SAMPLES) BIAS AUDIT")

    # Save reports to cache
    output_path = os.path.join(cache_dir, "dataset_bias_audit_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "pilot_report": pilot_report,
            "baseline_report": baseline_report
        }, f, indent=2)

    print(f"\n[+] Comprehensive bias report saved to: {output_path}")


if __name__ == "__main__":
    main()
