"""T.R.A.C.E. — UniversalFakeDetect (UnivFD) Offline Evaluation Module.

Phase 8: Offline Proof of Concept
Provides an isolated, reproducible test harness for evaluating the UnivFD model
architecture (Ojha et al., CVPR 2023) against a balanced calibration dataset.

IMPORTANT: This module is strictly for offline evaluation and is isolated from
the production FastAPI backend analysis pipeline.
"""

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

# Check dependency availability without crashing
TORCH_AVAILABLE = False
TORCHVISION_AVAILABLE = False
CLIP_AVAILABLE = False
PIL_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    pass

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    import torchvision.transforms as transforms
    TORCHVISION_AVAILABLE = True
except ImportError:
    pass

try:
    import clip
    CLIP_AVAILABLE = True
except ImportError:
    pass


# ==============================================================================
# Model Architecture (Ojha et al., CVPR 2023)
# ==============================================================================

if TORCH_AVAILABLE:
    class UnivFDModel(nn.Module):
        """
        UniversalFakeDetect (UnivFD) model architecture.
        Consists of a frozen visual backbone (CLIP ViT-L/14) and a trainable
        linear probe (Linear(768, 1)) trained on extracted feature embeddings.
        """
        def __init__(self, clip_model: nn.Module):
            super().__init__()
            self.clip_model = clip_model
            # Freeze visual backbone parameters
            for param in self.clip_model.parameters():
                param.requires_grad = False
            # Linear probe on 768-dim CLIP ViT-L/14 visual embedding
            self.fc = nn.Linear(768, 1)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            """
            Forward pass.
            Returns raw logit (unbounded real number).
            """
            with torch.no_grad():
                features = self.clip_model.encode_image(x)
                # Cast to float32 if backbone operates in float16
                features = features.to(torch.float32)
            logits = self.fc(features)
            return logits


# ==============================================================================
# Evaluation Harness & Metrics Calculation
# ==============================================================================

@dataclass
class SamplePrediction:
    sample_id: str
    image_path: str
    ground_truth: int  # 0 = authentic, 1 = synthetic
    raw_logit: float
    sigmoid_score: float  # uncalibrated heuristic score in [0.0, 1.0]
    predicted_label: int  # 0 = authentic, 1 = synthetic at threshold
    latency_ms: float
    source: str
    generator: str


def compute_roc_auc(scores: List[float], labels: List[int]) -> Optional[float]:
    """
    Computes Area Under the ROC Curve (ROC-AUC) using the trapezoidal rule
    without requiring external scikit-learn dependency.
    """
    if len(set(labels)) < 2:
        return None  # Cannot compute ROC-AUC with single class

    # Pair scores with ground-truth and sort descending by score
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

    # Calculate AUC using trapezoidal integration
    auc = 0.0
    for i in range(1, len(roc_points)):
        x_prev, y_prev = roc_points[i - 1]
        x_curr, y_curr = roc_points[i]
        auc += (x_curr - x_prev) * (y_prev + y_curr) / 2.0

    return round(auc, 4)


def compute_metrics(
    predictions: List[SamplePrediction],
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Computes standard binary classification performance metrics.
    """
    total = len(predictions)
    if total == 0:
        return {"error": "No predictions provided."}

    tp = sum(1 for p in predictions if p.ground_truth == 1 and p.predicted_label == 1)
    tn = sum(1 for p in predictions if p.ground_truth == 0 and p.predicted_label == 0)
    fp = sum(1 for p in predictions if p.ground_truth == 0 and p.predicted_label == 1)
    fn = sum(1 for p in predictions if p.ground_truth == 1 and p.predicted_label == 0)

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    scores = [p.sigmoid_score for p in predictions]
    labels = [p.ground_truth for p in predictions]
    roc_auc = compute_roc_auc(scores, labels)

    avg_latency = sum(p.latency_ms for p in predictions) / total

    return {
        "threshold": threshold,
        "sample_count": total,
        "confusion_matrix": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
        },
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall_sensitivity": round(recall, 4),
        "specificity": round(specificity, 4),
        "roc_auc": roc_auc,
        "avg_latency_ms": round(avg_latency, 2),
    }


# ==============================================================================
# Environment & Preflight Checks
# ==============================================================================

def check_environment() -> Dict[str, Any]:
    """Inspects the local runtime and reports dependencies readiness."""
    info = {
        "python_version": sys.version.split()[0],
        "torch_available": TORCH_AVAILABLE,
        "torch_version": torch.__version__ if TORCH_AVAILABLE else None,
        "torchvision_available": TORCHVISION_AVAILABLE,
        "clip_available": CLIP_AVAILABLE,
        "pil_available": PIL_AVAILABLE,
        "cuda_available": torch.cuda.is_available() if TORCH_AVAILABLE else False,
        "cuda_device_name": torch.cuda.get_device_name(0) if (TORCH_AVAILABLE and torch.cuda.is_available()) else None,
    }
    return info


def print_env_report():
    """Prints diagnostic report of current Python runtime."""
    env = check_environment()
    print("=" * 70)
    print("T.R.A.C.E. — UnivFD Environment Preflight Diagnostic")
    print("=" * 70)
    print(f"  Python Runtime:        {env['python_version']}")
    print(f"  PyTorch Installed:     {env['torch_available']} ({env['torch_version'] or 'Not installed'})")
    print(f"  Torchvision Installed: {env['torchvision_available']}")
    print(f"  OpenAI CLIP Installed: {env['clip_available']}")
    print(f"  Pillow Installed:      {env['pil_available']}")
    print(f"  CUDA Hardware Accel:   {env['cuda_available']} ({env['cuda_device_name'] or 'CPU only'})")
    print("=" * 70)

    if not (env["torch_available"] and env["torchvision_available"] and env["clip_available"]):
        print("\n[!] MISSING DEPENDENCIES FOR LOCAL OFFLINE INFERENCE:")
        print("    To run offline inference with UnivFD on this environment, install:")
        print("    pip install torch torchvision")
        print("    pip install git+https://github.com/openai/CLIP.git")
        print("=" * 70)


# ==============================================================================
# Execution Runner
# ==============================================================================

def run_evaluation(
    manifest_path: str,
    weights_path: str,
    threshold: float = 0.5,
    device_name: str = "cpu"
) -> int:
    """
    Executes evaluation across the manifest dataset using the verified model.
    """
    print_env_report()

    # Precondition 1: Check dependencies
    if not (TORCH_AVAILABLE and TORCHVISION_AVAILABLE and CLIP_AVAILABLE and PIL_AVAILABLE):
        print("\n[-] EXECUTION STOPPED: Required deep-learning dependencies are missing.")
        print("    Please review instructions above to configure dependencies safely.")
        return 1

    # Precondition 2: Check manifest existence
    if not os.path.exists(manifest_path):
        print(f"\n[-] ERROR: Dataset manifest not found at: {manifest_path}")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    samples = manifest.get("samples", [])
    if not samples:
        print(f"\n[-] ERROR: Manifest contains 0 samples: {manifest_path}")
        return 1

    print(f"\n[+] Loaded manifest with {len(samples)} samples from: {manifest_path}")

    # Precondition 3: Check weights existence
    if not os.path.exists(weights_path):
        print(f"\n[-] ERROR: Pretrained linear probe weights not found at: {weights_path}")
        print("    UnivFD requires the linear classification head ('fc_weights.pth').")
        print("    Download from documented source into: backend/evaluation/weights/fc_weights.pth")
        return 1

    # Initialize device
    device = torch.device(device_name if (device_name == "cuda" and torch.cuda.is_available()) else "cpu")
    print(f"[+] Initializing UnivFD on compute device: {device}")

    # Load visual backbone
    print("[+] Loading CLIP ViT-L/14 backbone (frozen)...")
    clip_model, clip_preprocess = clip.load("ViT-L/14", device=device)
    model = UnivFDModel(clip_model).to(device)

    # Load classification head weights
    print(f"[+] Loading linear probe weights from {weights_path}...")
    checkpoint = torch.load(weights_path, map_location=device, weights_only=True)
    if "fc" in checkpoint:
        model.fc.load_state_dict(checkpoint["fc"])
    elif "state_dict" in checkpoint:
        model.fc.load_state_dict(checkpoint["state_dict"])
    else:
        model.fc.load_state_dict(checkpoint)

    model.eval()

    # Run inference across samples
    predictions: List[SamplePrediction] = []
    missing_images = []

    print("\n--- Beginning Per-Image Inference ---")
    for sample in samples:
        sample_id = sample.get("id", "unknown")
        image_path = sample.get("image_path", "")
        ground_truth = int(sample.get("ground_truth", 0))
        source = sample.get("source_dataset", "unknown")
        generator = sample.get("generator_type", "unknown")

        if not os.path.exists(image_path):
            manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
            candidate1 = os.path.normpath(os.path.join(manifest_dir, image_path))
            repo_root = os.path.normpath(os.path.join(manifest_dir, "..", ".."))
            candidate2 = os.path.normpath(os.path.join(repo_root, image_path))
            if os.path.exists(candidate1):
                image_path = candidate1
            elif os.path.exists(candidate2):
                image_path = candidate2
            else:
                missing_images.append(image_path)
                continue

        try:
            image = Image.open(image_path).convert("RGB")
            image_tensor = clip_preprocess(image).unsqueeze(0).to(device)

            start_t = time.perf_counter()
            with torch.no_grad():
                logit_out = model(image_tensor)
                raw_logit = float(logit_out.squeeze().item())
                # Sigmoid gives an uncalibrated score in [0.0, 1.0]
                sigmoid_score = 1.0 / (1.0 + math.exp(-raw_logit))
            latency = (time.perf_counter() - start_t) * 1000.0

            pred_label = 1 if sigmoid_score >= threshold else 0

            predictions.append(SamplePrediction(
                sample_id=sample_id,
                image_path=image_path,
                ground_truth=ground_truth,
                raw_logit=round(raw_logit, 4),
                sigmoid_score=round(sigmoid_score, 4),
                predicted_label=pred_label,
                latency_ms=round(latency, 2),
                source=source,
                generator=generator
            ))

            print(
                f"  [{sample_id}] GT: {'SYNTHETIC' if ground_truth == 1 else 'AUTHENTIC ':<9} | "
                f"Raw Logit: {raw_logit:>7.3f} | Score: {sigmoid_score:>5.3f} | "
                f"Pred: {'SYNTHETIC' if pred_label == 1 else 'AUTHENTIC '} | {latency:>5.1f}ms"
            )

        except Exception as exc:
            print(f"  [-] Failed processing {image_path}: {exc}")

    if missing_images:
        print(f"\n[!] Notice: {len(missing_images)} / {len(samples)} images were missing on disk.")
        print("    Example missing path:", missing_images[0])
        print("    Please acquire dataset samples into the designated evaluation directory.")

    if not predictions:
        print("\n[-] No images were evaluated. Please populate dataset images.")
        return 1

    # Compute aggregate metrics
    metrics = compute_metrics(predictions, threshold)

    print("\n" + "=" * 70)
    print("T.R.A.C.E. — UniversalFakeDetect Evaluation Results")
    print("=" * 70)
    print(f"  Evaluated Samples:     {metrics['sample_count']}")
    print(f"  Classification Cutoff: {metrics['threshold']} (Uncalibrated heuristic threshold)")
    print(f"  Accuracy:              {metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision:             {metrics['precision'] * 100:.2f}%")
    print(f"  Recall (Sensitivity):  {metrics['recall_sensitivity'] * 100:.2f}%")
    print(f"  Specificity:           {metrics['specificity'] * 100:.2f}%")
    print(f"  ROC-AUC:               {metrics['roc_auc'] if metrics['roc_auc'] is not None else 'N/A'}")
    print(f"  Avg Inference Latency: {metrics['avg_latency_ms']:.2f} ms")
    print("-" * 70)
    print("  Confusion Matrix:")
    print(f"    True Positives (Detected Synthetics):  {metrics['confusion_matrix']['true_positives']}")
    print(f"    True Negatives (Identified Authentic): {metrics['confusion_matrix']['true_negatives']}")
    print(f"    False Positives (Real labeled Fake):   {metrics['confusion_matrix']['false_positives']}")
    print(f"    False Negatives (Fake labeled Real):   {metrics['confusion_matrix']['false_negatives']}")
    print("=" * 70)
    print("[!] FORENSIC CAVEAT: A small sample size (20 images) serves strictly for")
    print("    technical verification. It does NOT establish statistical generalization")
    print("    or operational accuracy against production media.")
    print("=" * 70)

    return 0


def run_single_image_inference(
    image_path: str,
    weights_path: str,
    threshold: float = 0.5,
    device_name: str = "cpu"
) -> int:
    """Runs a single-image smoke test using UnivFD without calling production APIs."""
    if not os.path.exists(image_path):
        print(f"[-] ERROR: Image not found: {image_path}")
        return 1

    if not os.path.exists(weights_path):
        print(f"[-] ERROR: Weights file not found: {weights_path}")
        return 1

    device = torch.device(device_name if (device_name == "cuda" and torch.cuda.is_available()) else "cpu")
    print(f"[+] Loading CLIP ViT-L/14 backbone on {device}...")
    clip_model, clip_preprocess = clip.load("ViT-L/14", device=device)
    model = UnivFDModel(clip_model).to(device)

    print(f"[+] Loading classifier state dict from {weights_path}...")
    state_dict = torch.load(weights_path, map_location=device, weights_only=True)
    if "fc" in state_dict:
        model.fc.load_state_dict(state_dict["fc"])
    elif "state_dict" in state_dict:
        model.fc.load_state_dict(state_dict["state_dict"])
    else:
        model.fc.load_state_dict(state_dict)

    model.eval()

    img = Image.open(image_path).convert("RGB")
    tensor = clip_preprocess(img).unsqueeze(0).to(device)

    start_t = time.perf_counter()
    with torch.no_grad():
        logit_tensor = model(tensor)
    latency_ms = (time.perf_counter() - start_t) * 1000.0

    raw_logit = float(logit_tensor.squeeze().item())
    sigmoid_score = 1.0 / (1.0 + math.exp(-raw_logit))
    predicted_class = "SYNTHETIC / AI-GENERATED" if sigmoid_score >= threshold else "AUTHENTIC / NON-SYNTHETIC"

    print("\n" + "=" * 70)
    print("T.R.A.C.E. — UniversalFakeDetect Single-Image Smoke Test")
    print("=" * 70)
    print(f"  Target Image:       {image_path} ({img.size[0]}x{img.size[1]} {img.mode})")
    print(f"  Model Architecture: CLIP ViT-L/14 + Linear(768, 1)")
    print(f"  Model Weights:      {weights_path}")
    print(f"  Raw Model Logit:    {raw_logit:.6f}")
    print(f"  Sigmoid Score:      {sigmoid_score:.6f} (uncalibrated heuristic score)")
    print(f"  Decision Threshold: {threshold}")
    print(f"  Prediction Class:   {predicted_class}")
    print(f"  Inference Latency:  {latency_ms:.2f} ms")
    print(f"  Is Finite:          {math.isfinite(raw_logit) and math.isfinite(sigmoid_score)}")
    print("=" * 70)
    print("[!] FORENSIC CAVEAT: Single-image inference proves only that the pipeline")
    print("    executes successfully. It does NOT establish manipulation detection accuracy.")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="T.R.A.C.E. UnivFD Offline Evaluation Harness")
    parser.add_argument(
        "--manifest",
        default="backend/evaluation/dataset_manifest_sample.json",
        help="Path to evaluation dataset manifest JSON"
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Path to a single image for smoke test inference"
    )
    parser.add_argument(
        "--weights",
        default="backend/evaluation/weights/fc_weights.pth",
        help="Path to UnivFD linear classification weights (.pth)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for sigmoid score (default: 0.5)"
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Compute device (default: cpu)"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Run environment and preflight diagnostic check only"
    )

    args = parser.parse_args()

    if args.check_env:
        print_env_report()
        sys.exit(0)

    if args.image:
        ret = run_single_image_inference(
            image_path=args.image,
            weights_path=args.weights,
            threshold=args.threshold,
            device_name=args.device
        )
        sys.exit(ret)

    ret = run_evaluation(
        manifest_path=args.manifest,
        weights_path=args.weights,
        threshold=args.threshold,
        device_name=args.device
    )
    sys.exit(ret)


if __name__ == "__main__":
    main()
