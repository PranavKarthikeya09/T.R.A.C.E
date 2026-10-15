# T.R.A.C.E. — UniversalFakeDetect (UnivFD) Offline Evaluation

This directory contains the isolated, offline evaluation harness for evaluating **UniversalFakeDetect (UnivFD)** (Ojha et al., CVPR 2023) within the T.R.A.C.E. project.

> [!IMPORTANT]
> This evaluation suite is strictly isolated from the production FastAPI backend. It does not replace Azure AI Foundry GPT-4.1 mini, does not modify runtime API contracts, and does not alter production dependencies.

---

## 1. Verified Model Verification & Metadata

| Attribute | Verified Value |
|---|---|
| **Model Name** | UniversalFakeDetect (UnivFD) |
| **Authors & Paper** | Utkarsh Ojha, Yuheng Li, Yong Jae Lee (*CVPR 2023*) |
| **Official Repository** | [`WisconsinAIVision/UniversalFakeDetect`](https://github.com/WisconsinAIVision/UniversalFakeDetect) |
| **Repository License** | **MIT License** (Permissive; permits commercial and non-commercial reuse) |
| **Backbone Architecture** | OpenAI CLIP `ViT-L/14` (frozen, 768-dimensional visual embedding) |
| **Classification Head** | Single linear layer `torch.nn.Linear(768, 1)` |
| **Pretrained Weights** | `fc_weights.pth` (~4 KB state dict containing `weight: [1, 768]` and `bias: [1]`) |
| **Mathematical Output** | Raw scalar **logit** ($z \in \mathbb{R}$); mapped to an uncalibrated score via $\sigma(z) = \frac{1}{1 + e^{-z}} \in [0.0, 1.0]$. |

> [!CAUTION]
> **Forensic Semantic Rule:** While $\sigma(z)$ is bounded within $[0.0, 1.0]$, it is an **uncalibrated heuristic score**, *not* a true calibrated Bayesian posterior probability. T.R.A.C.E. guidelines strictly forbid reporting uncalibrated scores as true probabilities.

---

## 2. Directory Layout

```
backend/evaluation/
├── README.md                          # This setup & protocol document
├── eval_univfd.py                     # Standalone CLI evaluation harness
├── dataset_manifest_sample.json       # 20-sample balanced dataset schema
├── weights/                           # Directory for downloaded weights
│   └── fc_weights.pth                 # (Expected checkpoint destination)
└── data/                              # Evaluation dataset images
    ├── authentic/                     # 10 verified camera captures
    └── synthetic/                     # 10 verified AI-generated images
```

---

## 3. Environment & Dependency Setup

The evaluation harness requires PyTorch and OpenAI CLIP. To run offline inference locally without altering `backend/requirements.txt`:

```powershell
# In the backend virtual environment:
cd backend
.\.venv\Scripts\Activate.ps1

# Install PyTorch and Torchvision (CPU or CUDA):
pip install torch torchvision

# Install OpenAI CLIP:
pip install git+https://github.com/openai/CLIP.git
```

---

## 4. Pretrained Weights Acquisition

1. Create the `weights/` folder:
   ```powershell
   mkdir -p backend/evaluation/weights
   ```
2. Download `fc_weights.pth` from the official repository or verified mirror:
   * Official GitHub: [WisconsinAIVision/UniversalFakeDetect (pretrained_weights)](https://github.com/WisconsinAIVision/UniversalFakeDetect)
   * Hugging Face Mirror: [siddharthksah/deepsafe-weights (universalfakedetect/fc_weights.pth)](https://huggingface.co/siddharthksah/deepsafe-weights/tree/main/universalfakedetect)
3. Place the file at: `backend/evaluation/weights/fc_weights.pth`.

---

## 5. Dataset Manifest Format

Evaluation data is specified via a deterministic JSON manifest (`dataset_manifest_sample.json`):

```json
{
  "id": "synth_01",
  "image_path": "data/synthetic/genimage_sd14_001.png",
  "ground_truth": 1,
  "source_dataset": "GenImage (ECCV 2024)",
  "generator_type": "Stable Diffusion v1.4",
  "notes": "Latent diffusion model, text-to-image 512x512"
}
```

* `ground_truth = 0`: Verified authentic camera photograph.
* `ground_truth = 1`: Verified synthetic / AI-generated image.

---

## 6. Running the Evaluation Harness

### 1. Preflight Environment Check
Verify runtime dependencies without loading data:
```powershell
python backend/evaluation/eval_univfd.py --check-env
```

### 2. Full Evaluation Run
Execute evaluation across the manifest (default threshold = 0.5):
```powershell
python backend/evaluation/eval_univfd.py `
  --manifest backend/evaluation/dataset_manifest_sample.json `
  --weights backend/evaluation/weights/fc_weights.pth `
  --threshold 0.5 `
  --device cpu
```

---

## 7. Performance Metrics Computed

The harness outputs:
* **Per-sample diagnostics:** Sample ID, ground truth, raw logit, sigmoid score, predicted class, and latency in milliseconds.
* **Accuracy:** Overall correct predictions over total samples.
* **Precision:** $\frac{TP}{TP + FP}$ (purity of synthetic predictions).
* **Recall / Sensitivity:** $\frac{TP}{TP + FN}$ (ability to flag synthetic media).
* **Specificity:** $\frac{TN}{TN + FP}$ (ability to avoid false-flagging authentic media).
* **Confusion Matrix:** Explicit counts of TP, TN, FP, and FN.
* **ROC-AUC:** Area under the ROC curve calculated via trapezoidal integration.
* **Inference Latency:** Average inference runtime per image in milliseconds.
