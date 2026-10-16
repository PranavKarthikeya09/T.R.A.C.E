"""T.R.A.C.E. — Phase 17: Controlled Preprocessing Audit and Evaluation.

Implements non-destructive, reproducible preprocessing variants:
  Variant A: Baseline Original Image with default CLIP preprocessing
  Variant B: Consistent RGB Normalization (palette/transparency stripping)
  Variant C: Common Resolution (512x512 center crop, bicubic)
  Variant D: Controlled JPEG Re-encoding (Quality = 85, 4:2:0 subsampling)
  Variant E: Combined Common Resolution (512x512) + Controlled JPEG (Q=85)

Evaluates the existing UnivFD checkpoint on the pilot and baseline datasets
under all variants using unrounded raw scores for ROC-AUC calculation.
Derived files are saved strictly in the git-ignored cache directory:
  backend/evaluation/cache/derived_variants/
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

try:
    import torch
    import torch.nn as nn
    import clip
except ImportError as err:
    print(f"[-] Deep learning dependencies missing: {err}")
    sys.exit(1)


# ==============================================================================
# Model Architecture (Ojha et al., CVPR 2023)
# ==============================================================================

class UnivFDModel(nn.Module):
    def __init__(self, clip_model: nn.Module):
        super().__init__()
        self.clip_model = clip_model
        for param in self.clip_model.parameters():
            param.requires_grad = False
        self.fc = nn.Linear(768, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            features = self.clip_model.encode_image(x)
            features = features.to(torch.float32)
        logits = self.fc(features)
        return logits


# ==============================================================================
# Unrounded ROC-AUC and Metric Calculation
# ==============================================================================

def compute_roc_auc_unrounded(scores: List[float], labels: List[int]) -> Optional[float]:
    """Computes exact Area Under the ROC Curve without score rounding or ties distortion."""
    if len(set(labels)) < 2:
        return None

    paired = sorted(zip(scores, labels), key=lambda p: p[0], reverse=True)
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count

    if pos_count == 0 or neg_count == 0:
        return None

    tp = 0
    fp = 0
    roc_points = [(0.0, 0.0)]

    for _, label in paired:
        if label == 1:
            tp += 1
        else:
            fp += 1
        fpr = fp / neg_count
        tpr = tp / pos_count
        roc_points.append((fpr, tpr))

    auc = 0.0
    for i in range(1, len(roc_points)):
        x_prev, y_prev = roc_points[i - 1]
        x_curr, y_curr = roc_points[i]
        auc += (x_curr - x_prev) * (y_prev + y_curr) / 2.0

    return auc


@dataclass
class EvalSampleRecord:
    sample_id: str
    ground_truth: int
    raw_logit: float
    sigmoid_score: float
    pred_label: int
    latency_ms: float
    generator_family: str
    split: str
    is_held_out: bool
    source_dataset: str


def compute_comprehensive_metrics(
    records: List[EvalSampleRecord],
    threshold: float = 0.5
) -> Dict[str, Any]:
    total = len(records)
    if total == 0:
        return {"error": "No records to evaluate"}

    tp = sum(1 for r in records if r.ground_truth == 1 and r.pred_label == 1)
    tn = sum(1 for r in records if r.ground_truth == 0 and r.pred_label == 0)
    fp = sum(1 for r in records if r.ground_truth == 0 and r.pred_label == 1)
    fn = sum(1 for r in records if r.ground_truth == 1 and r.pred_label == 0)

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    scores = [r.sigmoid_score for r in records]
    labels = [r.ground_truth for r in records]
    roc_auc_unrounded = compute_roc_auc_unrounded(scores, labels)

    avg_latency = sum(r.latency_ms for r in records) / total

    # Per-generator breakdown
    gen_families = sorted(list(set(r.generator_family for r in records if r.ground_truth == 1)))
    per_gen_metrics = {}
    for gen in gen_families:
        gen_recs = [r for r in records if r.generator_family == gen]
        gen_tp = sum(1 for r in gen_recs if r.pred_label == 1)
        per_gen_metrics[gen] = {
            "total": len(gen_recs),
            "detected": gen_tp,
            "recall": round(gen_tp / len(gen_recs), 4) if gen_recs else 0.0,
            "mean_score": round(sum(r.sigmoid_score for r in gen_recs) / len(gen_recs), 4) if gen_recs else 0.0,
        }

    # Held-out vs In-distribution breakdown (if applicable)
    held_out_recs = [r for r in records if r.is_held_out and r.ground_truth == 1]
    in_dist_synth = [r for r in records if (not r.is_held_out) and r.ground_truth == 1]

    held_out_recall = (sum(1 for r in held_out_recs if r.pred_label == 1) / len(held_out_recs)) if held_out_recs else None
    in_dist_recall = (sum(1 for r in in_dist_synth if r.pred_label == 1) / len(in_dist_synth)) if in_dist_synth else None

    return {
        "sample_count": total,
        "threshold": threshold,
        "confusion_matrix": {
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
        },
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "roc_auc_unrounded": roc_auc_unrounded,
        "roc_auc_display": round(roc_auc_unrounded, 4) if roc_auc_unrounded is not None else None,
        "avg_latency_ms": round(avg_latency, 2),
        "per_generator_recall": per_gen_metrics,
        "held_out_synth_recall": round(held_out_recall, 4) if held_out_recall is not None else None,
        "in_distribution_synth_recall": round(in_dist_recall, 4) if in_dist_recall is not None else None,
    }


# ==============================================================================
# Non-Destructive Controlled Preprocessing Transformations
# ==============================================================================

def apply_variant_transform(
    src_img_path: str,
    variant_id: str,
    output_dir: str,
    sample_id: str
) -> Tuple[Image.Image, str, Dict[str, Any]]:
    """
    Applies the specified controlled transformation non-destructively,
    saves the derived variant to output_dir, and returns the PIL Image object,
    the saved path, and a transformation log dictionary.
    """
    os.makedirs(output_dir, exist_ok=True)

    with Image.open(src_img_path) as raw_img:
        orig_format = raw_img.format or "UNKNOWN"
        orig_mode = raw_img.mode
        orig_size = raw_img.size

        if variant_id == "variant_a_baseline":
            # Variant A: Baseline - Original image opened and converted to RGB in memory
            # No persistent alteration
            img_rgb = raw_img.convert("RGB")
            out_path = src_img_path  # Evaluates source image directly
            transform_log = {
                "variant": "Variant A (Default CLIP Preprocessing)",
                "source_format": orig_format,
                "source_mode": orig_mode,
                "source_size": orig_size,
                "persistent_file_saved": False,
                "actions": ["In-memory RGB conversion", "CLIP ViT-L/14 bicubic 224 resize & center crop"]
            }
            return img_rgb, out_path, transform_log

        elif variant_id == "variant_b_consistent_rgb":
            # Variant B: Consistent RGB conversion stripping palette/alpha
            out_filename = f"{sample_id}_rgb.png"
            out_path = os.path.join(output_dir, out_filename)

            if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
                # Composite transparent images over solid neutral white background
                rgba = raw_img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[3])
                img_rgb = background
            else:
                img_rgb = raw_img.convert("RGB")

            img_rgb.save(out_path, format="PNG", optimize=False)
            transform_log = {
                "variant": "Variant B (Consistent RGB Normalization)",
                "source_mode": orig_mode,
                "target_mode": "RGB",
                "target_format": "PNG",
                "derived_path": out_path,
                "actions": ["Normalized to pure 24-bit RGB", "Stripped indexed palettes and alpha channels", "Lossless PNG container"]
            }
            return img_rgb, out_path, transform_log

        elif variant_id == "variant_c_res512":
            # Variant C: Consistent Resizing & Center Crop to 512x512
            out_filename = f"{sample_id}_512x512.png"
            out_path = os.path.join(output_dir, out_filename)

            img_rgb = raw_img.convert("RGB")
            # Scale smaller dimension to 512 maintaining aspect ratio, then center crop 512x512
            w, h = img_rgb.size
            scale = 512.0 / min(w, h)
            new_w, new_h = int(round(w * scale)), int(round(h * scale))
            img_resized = img_rgb.resize((new_w, new_h), Image.Resampling.BICUBIC)

            # Center crop 512x512
            left = (new_w - 512) // 2
            top = (new_h - 512) // 2
            img_cropped = img_resized.crop((left, top, left + 512, top + 512))

            img_cropped.save(out_path, format="PNG", optimize=False)
            transform_log = {
                "variant": "Variant C (Common 512x512 Resolution & Center Crop)",
                "source_size": orig_size,
                "intermediate_size": (new_w, new_h),
                "target_size": (512, 512),
                "resampling": "Bicubic",
                "target_format": "PNG",
                "derived_path": out_path,
                "actions": ["Isotropic resize smaller edge to 512", "Center crop 512x512", "Lossless PNG container"]
            }
            return img_cropped, out_path, transform_log

        elif variant_id == "variant_d_jpeg_q85":
            # Variant D: Controlled JPEG re-encoding at documented Quality 85
            out_filename = f"{sample_id}_q85.jpg"
            out_path = os.path.join(output_dir, out_filename)

            img_rgb = raw_img.convert("RGB")
            # Save at quality 85, 4:2:0 subsampling, standard baseline
            img_rgb.save(out_path, format="JPEG", quality=85, subsampling="4:2:0", optimize=True)

            # Reload from disk to evaluate exact decoded JPEG pixels
            img_reloaded = Image.open(out_path).convert("RGB")
            transform_log = {
                "variant": "Variant D (Controlled JPEG Standardization Q=85)",
                "source_format": orig_format,
                "target_format": "JPEG",
                "quality": 85,
                "subsampling": "4:2:0",
                "derived_path": out_path,
                "actions": ["RGB conversion", "JPEG DCT quantization at Q=85", "Decoded JPEG pixel evaluation"]
            }
            return img_reloaded, out_path, transform_log

        elif variant_id == "variant_e_res512_jpeg_q85":
            # Variant E: Combined Common Resolution (512x512) + JPEG Q=85
            out_filename = f"{sample_id}_512x512_q85.jpg"
            out_path = os.path.join(output_dir, out_filename)

            img_rgb = raw_img.convert("RGB")
            w, h = img_rgb.size
            scale = 512.0 / min(w, h)
            new_w, new_h = int(round(w * scale)), int(round(h * scale))
            img_resized = img_rgb.resize((new_w, new_h), Image.Resampling.BICUBIC)

            left = (new_w - 512) // 2
            top = (new_h - 512) // 2
            img_cropped = img_resized.crop((left, top, left + 512, top + 512))

            img_cropped.save(out_path, format="JPEG", quality=85, subsampling="4:2:0", optimize=True)
            img_reloaded = Image.open(out_path).convert("RGB")
            transform_log = {
                "variant": "Variant E (Combined Common 512x512 + JPEG Q=85)",
                "target_size": (512, 512),
                "target_format": "JPEG",
                "quality": 85,
                "derived_path": out_path,
                "actions": ["Isotropic 512 resize & center crop", "JPEG Q=85 DCT compression", "Decoded JPEG evaluation"]
            }
            return img_reloaded, out_path, transform_log

        else:
            raise ValueError(f"Unknown variant ID: {variant_id}")


# ==============================================================================
# Evaluation Runner Across Variants
# ==============================================================================

VARIANTS = [
    ("variant_a_baseline", "Variant A: Default CLIP Preprocessing (Original Images)"),
    ("variant_b_consistent_rgb", "Variant B: Consistent RGB Normalization (Transparency/Palette Stripped)"),
    ("variant_c_res512", "Variant C: Common Resolution (512x512 Bicubic Center Crop)"),
    ("variant_d_jpeg_q85", "Variant D: Controlled JPEG Standardization (Quality=85, 4:2:0)"),
    ("variant_e_res512_jpeg_q85", "Variant E: Combined Common 512x512 + JPEG Q=85"),
]


def run_controlled_preprocessing_eval(
    manifest_path: str,
    weights_path: str,
    repo_root: str,
    threshold: float = 0.5,
    device_name: str = "cpu"
) -> Dict[str, Any]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    samples = manifest.get("samples", [])
    if not samples:
        raise ValueError(f"No samples found in {manifest_path}")

    device = torch.device(device_name if (device_name == "cuda" and torch.cuda.is_available()) else "cpu")
    print(f"[+] Loading frozen CLIP ViT-L/14 backbone onto {device}...")
    clip_model, clip_preprocess = clip.load("ViT-L/14", device=device)
    model = UnivFDModel(clip_model).to(device)

    print(f"[+] Loading UnivFD linear head weights from: {weights_path}...")
    ckpt = torch.load(weights_path, map_location=device, weights_only=True)
    if "fc" in ckpt:
        model.fc.load_state_dict(ckpt["fc"])
    elif "state_dict" in ckpt:
        model.fc.load_state_dict(ckpt["state_dict"])
    else:
        model.fc.load_state_dict(ckpt)
    model.eval()

    cache_derived_dir = os.path.join(repo_root, "backend", "evaluation", "cache", "derived_variants")
    os.makedirs(cache_derived_dir, exist_ok=True)

    variant_results = {}
    variant_transform_logs = {}

    for var_id, var_name in VARIANTS:
        print("\n" + "=" * 80)
        print(f"RUNNING EVALUATION: {var_name}")
        print("=" * 80)

        var_out_dir = os.path.join(cache_derived_dir, var_id)
        records: List[EvalSampleRecord] = []
        var_logs = []

        start_var_t = time.perf_counter()
        for idx, sample in enumerate(samples, 1):
            s_id = sample["id"]
            gt = int(sample["ground_truth"])
            gen = sample.get("generator_family", sample.get("generator_type", "none"))
            split = sample.get("split", "test")
            is_held_out = sample.get("is_held_out", False)
            src_ds = sample.get("source_dataset", "unknown")

            raw_path = os.path.normpath(os.path.join(repo_root, sample["image_path"]))
            if not os.path.exists(raw_path):
                raise FileNotFoundError(f"Missing source file: {raw_path}")

            # Apply non-destructive controlled preprocessing
            img_obj, saved_path, t_log = apply_variant_transform(
                src_img_path=raw_path,
                variant_id=var_id,
                output_dir=var_out_dir,
                sample_id=s_id
            )
            var_logs.append(t_log)

            # Preprocess tensor for CLIP
            tensor = clip_preprocess(img_obj).unsqueeze(0).to(device)

            infer_start = time.perf_counter()
            with torch.no_grad():
                logit_out = model(tensor)
                raw_logit = float(logit_out.squeeze().item())
                # Exact unrounded sigmoid
                sigmoid_score = 1.0 / (1.0 + math.exp(-raw_logit))
            latency_ms = (time.perf_counter() - infer_start) * 1000.0

            pred_label = 1 if sigmoid_score >= threshold else 0

            records.append(EvalSampleRecord(
                sample_id=s_id,
                ground_truth=gt,
                raw_logit=raw_logit,
                sigmoid_score=sigmoid_score,
                pred_label=pred_label,
                latency_ms=latency_ms,
                generator_family=gen,
                split=split,
                is_held_out=is_held_out,
                source_dataset=src_ds,
            ))

            gt_str = "SYNTH" if gt == 1 else "AUTH"
            pred_str = "SYNTH" if pred_label == 1 else "AUTH"
            print(f"  [{idx:02d}/{len(samples):02d}] {s_id:<28} | GT: {gt_str} | Logit: {raw_logit:>7.3f} | Score: {sigmoid_score:>6.4f} | Pred: {pred_str} | {latency_ms:>5.1f}ms")

        var_duration = time.perf_counter() - start_var_t
        metrics = compute_comprehensive_metrics(records, threshold)
        metrics["total_duration_seconds"] = round(var_duration, 2)
        variant_results[var_id] = {
            "name": var_name,
            "metrics": metrics,
            "records": [
                {
                    "sample_id": r.sample_id,
                    "ground_truth": r.ground_truth,
                    "raw_logit": r.raw_logit,
                    "sigmoid_score": r.sigmoid_score,
                    "pred_label": r.pred_label,
                    "generator_family": r.generator_family,
                    "split": r.split,
                    "is_held_out": r.is_held_out
                }
                for r in records
            ]
        }
        variant_transform_logs[var_id] = var_logs

        print(f"\n--- Summary for {var_name} ---")
        print(f"  Accuracy:    {metrics['accuracy'] * 100:.2f}%")
        print(f"  Precision:   {metrics['precision'] * 100:.2f}%")
        print(f"  Recall:      {metrics['recall'] * 100:.2f}% (TP={metrics['confusion_matrix']['tp']}/{metrics['confusion_matrix']['tp'] + metrics['confusion_matrix']['fn']})")
        print(f"  Specificity: {metrics['specificity'] * 100:.2f}% (TN={metrics['confusion_matrix']['tn']}/{metrics['confusion_matrix']['tn'] + metrics['confusion_matrix']['fp']})")
        print(f"  ROC-AUC:     {metrics['roc_auc_display']} (Unrounded: {metrics['roc_auc_unrounded']:.6f})")
        if metrics['held_out_synth_recall'] is not None:
            print(f"  Held-Out Synthetic Recall: {metrics['held_out_synth_recall'] * 100:.2f}%")
        if metrics['in_distribution_synth_recall'] is not None:
            print(f"  In-Distribution Synthetic Recall: {metrics['in_distribution_synth_recall'] * 100:.2f}%")
        print(f"  Per-Generator Recall: {metrics['per_generator_recall']}")

    return {
        "manifest_path": manifest_path,
        "sample_count": len(samples),
        "threshold": threshold,
        "variant_results": variant_results,
        "variant_transform_logs": variant_transform_logs,
    }


def main():
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pilot_manifest = os.path.join(os.path.dirname(__file__), "pilot_manifest.json")
    baseline_manifest = os.path.join(os.path.dirname(__file__), "dataset_manifest.json")
    weights_path = os.path.join(os.path.dirname(__file__), "weights", "fc_weights.pth")
    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
    os.makedirs(cache_dir, exist_ok=True)

    print("================================================================================")
    print("T.R.A.C.E. — Phase 17: Controlled Preprocessing Audit on Pilot Dataset (40 Samples)")
    print("================================================================================")

    pilot_eval_output = run_controlled_preprocessing_eval(
        manifest_path=pilot_manifest,
        weights_path=weights_path,
        repo_root=repo_root,
        threshold=0.5,
        device_name="cpu"
    )

    # Save results to cache JSON
    results_file = os.path.join(cache_dir, "controlled_preprocessing_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(pilot_eval_output, f, indent=2)

    print(f"\n[+] Full controlled preprocessing audit results saved to: {results_file}")


if __name__ == "__main__":
    main()
