# T.R.A.C.E. — Phase 15: Leakage-Aware Dataset & Training Pipeline Specification

---

## 1. Dataset Source and Licensing Audit

| Dataset / Source | Access Method | Provenance & Evidence | License & Usage Terms | Redistribution & Local Evaluation | Authenticity / Generator Limitations | Windows Feasibility |
|---|---|---|---|---|---|---|
| **MS-COCO 2017 Validation** | Direct HTTP GET (`http://images.cocodataset.org/val2017/<id>.jpg`) | Real-world photography sourced from Flickr, vetted by MS-COCO consortium (2014–2017). | CC BY 4.0 (COCO metadata); individual Flickr photos under CC licenses / public domain. | Local research evaluation permitted. Full commercial redistribution of Flickr images subject to original author rights. | Authentic camera captures predate modern generative diffusion (collected $\le 2015$). Contains JPEG compression artifacts from original Flickr uploads. | Excellent (direct fast HTTP retrieval via `urllib`/`httpx`). |
| **RAISE Forensic Database** | Official university server (`http://l逆.inf.unifi.it/raise/` - Dang-Nguyen et al.) | 8,156 uncompressed camera RAW (TIFF/NEF) files from 3 controlled digital cameras (Nikon D90, D7000, D40). | Free for academic, scientific, and educational research only. Commercial redistribution restricted. | Local evaluation permitted for research. Direct public redistribution restricted. | Gold standard camera provenance; verified hardware sensor noise. Native RAW files are 15–30 MB each; pre-exported TIFF/JPEG crops preferred for transfer feasibility. | Moderate (requires robust HTTP timeout/retry handling due to academic server latency). |
| **Kodak PhotoCD Suite (PCD0992)** | Rich Franzen archive (`https://r0k.us/graphics/kodak/kodak/`) | 24 reference photographic images digitized directly from film/DCS digital cameras by Eastman Kodak (1993). | Public domain / royalty-free research benchmark. | Full redistribution and evaluation permitted. | Gold standard pristine reference photography, but strictly limited to $N = 24$ total images. | Excellent (instant HTTP retrieval, ~600–800 KB per uncompressed PNG). |
| **ForenSynths (Wang et al., CVPR 2020)** | GitHub (`PeterWang512/CNNDetection`) + official repository mirrors | ProGAN (LSUN), StyleGAN, BigGAN, CycleGAN synthetic images paired with LSUN/ImageNet real images. | BSD 2-Clause License on code; dataset images derived from open-source GANs and public datasets. | Academic research evaluation permitted. | Full dataset is 19 GB packaged in 7z archives. Individual GitHub samples are limited; automated batch retrieval requires mirror querying or targeted archive slicing. | Good (7z decompression or direct archive mirror extraction). |
| **Stable Diffusion (v1.4 / v1.5)** | Hugging Face Diffusers documentation & release assets (`huggingface/documentation-images`) | Latent diffusion text-to-image synthesis from CompVis / RunwayML / Stability AI release weights. | CreativeML OpenRAIL-M (permissive for research and evaluation with behavioral use restrictions). | Local evaluation permitted. | Official documentation images are curated, high-aesthetic outputs; they do not represent low-quality generation artifacts. | Excellent (direct HTTP retrieval via HF resolve endpoints). |
| **Stable Diffusion XL (SDXL Base 1.0)** | Hugging Face Diffusers documentation & Stability AI release assets | High-resolution latent diffusion ($1024\times 1024$) by Stability AI. | CreativeML OpenRAIL++ | Local evaluation permitted. | Primarily prompts representing cinematic and realistic styles. Text prompts documented in blog posts. | Excellent (direct HTTP retrieval). |
| **Kandinsky (2.2 / 3.0)** | Hugging Face Diffusers documentation & SberAI assets | Latent prior diffusion model synthesizing from text prompts via CLIP image prior. | Apache 2.0 License | Permitted for evaluation and redistribution under Apache 2.0. | Curated sample outputs showcasing prompt fidelity. | Excellent (direct HTTP retrieval). |
| **GLIGEN (Grounded Diffusion)** | Hugging Face Diffusers documentation (`diffusers/gligen/`) | Grounded text-to-image diffusion conditioning on bounding-box layouts (Li et al., CVPR 2023). | Apache 2.0 License / Diffusers | Local evaluation permitted. | Synthesized with spatial layout constraints. | Excellent (direct HTTP retrieval). |
| **FLUX.1 (Black Forest Labs)** | Hugging Face Diffusers documentation & BFL release samples | Next-generation rectified flow Diffusion Transformer (DiT) architecture. | FLUX.1-dev Non-Commercial License (research and evaluation permitted; commercial deployment restricted). | Non-commercial evaluation permitted. | State-of-the-art flow matching model. High-frequency textures closely mimic natural camera detail. | Excellent (direct HTTP retrieval). |
| **PixArt-$\alpha$ (Huawei Noah's Ark)** | Hugging Face Diffusers documentation & PixArt release assets | Diffusion Transformer (DiT) text-to-image synthesis using T5 text embeddings. | Apache 2.0 License | Permitted for evaluation and redistribution. | DiT patchified architecture leaves distinct structural signatures from traditional convolutional U-Nets. | Excellent (direct HTTP retrieval). |

---

## 2. Manifest Schema Specification

The dataset will be governed by [backend/evaluation/dataset_manifest_schema.json](file:///c:/Users/PRANAV%20KARTHIKEYA/OneDrive/Desktop/T.R.A.C.E/backend/evaluation/dataset_manifest_schema.json) (Draft-07 compliant).

### Key Fields & Separation of Concerns

1. **Deterministic Identity:**
   - `id`: Format `<class>_<source>_<hash8>` (e.g. `auth_coco_7f8a9b1c`, `synth_sd15_44335da8`).
   - `sha256`: Hexadecimal SHA-256 string calculated across exact file bytes.
2. **Ground-Truth Rigor:**
   - `ground_truth`: Binary integer (`0` = authentic, `1` = synthetic).
   - `label_rationale`: Human-verifiable explanation of why the label is trustworthy (e.g. *"Digitized from Kodak DCS digital sensor in 1993, pre-dating deep-learning synthesis"*).
3. **Partition Isolation:**
   - `split`: Enumerated string (`train`, `val`, `test`).
   - `is_held_out`: Boolean flag explicitly indicating if the sample's generator family is held out from training.
4. **Separation from Model Input:**
   - Model feature extractors consume **only** raw image pixels from `image_path`.
   - Metadata (`generator_family`, `semantic_category`, `source_dataset`, `license`, `generation_prompt`) is isolated and consumed strictly by the evaluation reporting engine.

---

## 3. Data Leakage and Source-Bias Prevention Plan

### 3.1 Cryptographic and Perceptual Deduplication

1. **Exact Byte Matching:** Automated verification that no two images share an identical SHA-256 hash across the entire dataset.
2. **Perceptual Deduplication (pHash):** 
   - Compute perceptual hash ($64$-bit DCT pHash) for all images.
   - Any pair with Hamming distance $\le 4$ is flagged as a near-duplicate and excluded across splits.
3. **Split Integrity:** 
   - No subject, prompt, or scene composition from `train` or `val` may appear in `test`.

### 3.2 Confounding Source & Format Shortcuts

A major vulnerability in deepfake benchmarks is that classifiers inadvertently learn image formats, resolutions, or host compression artifacts instead of generative signatures.

```
Confounding Risk:
[Authentic: All 640x480 Flickr JPEGs]  vs  [Synthetic: All 512x512 Uncompressed PNGs]
                    └──► Classifier learns: "PNG = Fake, JPEG = Real" (Shortcut!)
```

### Bias Mitigation Protocol

1. **Resolution Matching:** Both classes must span overlapping resolution tiers:
   - Tier A ($256\times 256$ to $384\times 384$): ProGAN, DDPM vs. RAISE / COCO small crops.
   - Tier B ($512\times 512$ to $768\times 768$): SD 1.5, Kandinsky vs. Kodak ($768\times 512$) and COCO ($640\times 480$).
   - Tier C ($1024\times 1024$): SDXL, FLUX.1 vs. RAISE high-resolution camera crops.
2. **Container Format Distribution:**
   - Authentic: ~60% JPEG (COCO, RAISE), ~40% PNG/TIFF (Kodak, RAISE).
   - Synthetic: ~60% JPEG (SDXL, FLUX, Diffusers), ~40% PNG (ProGAN, SD 1.5, Kandinsky).
3. **Pre-Training Statistical Independence Check:**
   - Before model training, compute a Chi-square independence test ($\chi^2$) and mutual information score between the binary label and:
     - Image width $\times$ height.
     - Container format (JPEG vs. PNG).
     - Compression quantization table presence.
   - If mutual information $I(\text{Label}; \text{Format}) > 0.1$, rebalance the file distribution before proceeding.
4. **Normalization Disclaimer:**
   - CLIP preprocessing resizes images to $224\times 224$ with bicubic interpolation and applies ImageNet normalization.
   - **Crucial Note:** Resampling does **not** erase high-frequency forensic artifacts or compression ringing; it introduces anti-aliasing filtering. Therefore, balancing the raw input formats is mandatory.

---

## 4. Held-Out-Generator Split Design

### Generator Partitioning Matrix

| Split | Partition Role | Authentic Sources ($N = 200$) | Synthetic Generators ($N = 200$) | Total Images |
|---|---|---|---|---|
| **Train** | Linear head parameter optimization | **100 images:**<br>• 50 MS-COCO<br>• 38 RAISE<br>• 12 Kodak | **100 images:**<br>• 25 GANs (ProGAN, StyleGAN2)<br>• 25 Latent Diffusion (SD v1.4, v1.5)<br>• 25 High-Res Diffusion (SDXL Base 1.0)<br>• 25 Cascaded/Prior (Kandinsky 2.2, GLIGEN)<br>*[FLUX.1 & PixArt strictly excluded]* | **200 images** (50%) |
| **Validation** | Hyperparameter tuning & threshold $\tau^*$ selection | **40 images:**<br>• 20 MS-COCO<br>• 14 RAISE<br>• 6 Kodak | **40 images:**<br>• 10 GANs<br>• 10 Latent Diffusion (SD v1.5)<br>• 10 High-Res Diffusion (SDXL)<br>• 10 Cascaded/Prior (Kandinsky 2.2)<br>*[FLUX.1 & PixArt strictly excluded]* | **80 images** (20%) |
| **Final Test** | Final unbiased evaluation | **60 images:**<br>• 30 MS-COCO<br>• 24 RAISE<br>• 6 Kodak | **60 images:**<br>• 20 In-Distribution Generators (5 GAN, 5 SD1.5, 5 SDXL, 5 Kandinsky)<br>• **40 HELD-OUT GENERATORS:**<br>  - 20 FLUX.1 (Diffusion Transformer / Flow Matching)<br>  - 20 PixArt-$\alpha$ (Diffusion Transformer) | **120 images** (30%) |

### Reporting Protocol
Final test metrics will be disaggregated into:
- **Result A: In-Distribution Synthetic Test Recall:** Measures retention on seen generator architectures (GAN, SD1.5, SDXL, Kandinsky).
- **Result B: Held-Out Generator Test Recall:** Measures true cross-architecture generalization to unseen Diffusion Transformers (FLUX.1, PixArt).
- **Result C: Per-Source Authentic Specificity:** Sliced across MS-COCO, RAISE, and Kodak to detect camera/host bias.

---

## 5. Training and Evaluation Pipeline Interface

The pipeline will be structured into three isolated, deterministic scripts under `backend/evaluation/`:

```
backend/evaluation/
├── extract_features.py       # Pre-computes and caches frozen CLIP ViT-L/14 embeddings
├── train_linear_probe.py     # Fits linear head on cached features using Validation thresholding
└── eval_pipeline.py          # Dual evaluation of Model A (UnivFD) and Model B (Multi-Gen)
```

### Script Specifications

#### 1. `extract_features.py`
- Loads frozen CLIP `ViT-L/14` on CPU/GPU.
- Iterates over `dataset_manifest.json`, extracts 768-dim float32 embeddings from `clip_model.encode_image(clip_preprocess(img))`.
- Saves cached features to `backend/evaluation/cache/clip_features.pt`:
  ```python
  {
      "sample_id": str,
      "embedding": torch.Tensor, # shape: [768], float32
      "ground_truth": int,
      "split": str,              # "train", "val", "test"
      "generator_family": str,
      "sha256": str
  }
  ```
- Fast caching: Runtime is ~5 minutes on CPU once. Subsequent experiments reuse the cache.

#### 2. `train_linear_probe.py`
- Loads `train` and `val` partitions from cache.
- Model architecture: `nn.Linear(768, 1)`.
- Loss: `nn.BCEWithLogitsLoss()`.
- Optimization: L-BFGS or AdamW ($\text{lr} = 10^{-3}$, weight decay $= 10^{-2}$).
- Early stopping on validation loss (patience = 10 epochs).
- Computes optimal decision threshold $\tau^*$ on validation set maximizing Youden's $J = \text{TPR} - \text{FPR}$.
- Saves checkpoint with complete provenance metadata to `backend/evaluation/weights/fc_weights_multigen_v1.pth`:
  ```python
  {
      "fc": {"weight": tensor([1, 768]), "bias": tensor([1])},
      "metadata": {
          "trained_on": ["progan", "stylegan2", "sd15", "sdxl", "kandinsky"],
          "held_out": ["flux", "pixart"],
          "val_threshold": float(tau_star),
          "training_samples": 200,
          "random_seed": 42,
          "backbone": "OpenAI-CLIP-ViT-L-14"
      }
  }
  ```

#### 3. `eval_pipeline.py`
- Evaluates both checkpoints on the identical `test` partition (120 images).
- Uses **unrounded 64-bit floating point scores** for trapezoidal ROC-AUC integration.
- Supports `--output-results <path.json>` saving per-sample raw logit, uncalibrated score, predicted label, latency, and ground truth.

---

## 6. Predefined Acceptance Criteria Review

| Metric | Target Gate | Proof-of-Concept Rationale | Why NOT a Production Guarantee |
|---|---|---|---|
| **Held-Out Generator Recall** *(FLUX.1 / PixArt)* | **$\ge 60.0\%$** | UnivFD baseline achieved **0.0%** on modern flow/diffusion transformers. Reaching 60% proves that multi-generator training materially expands the feature manifold beyond GANs. | A 40% false-negative rate on unseen generators remains unsafe for high-stakes forensic verification. |
| **In-Distribution Synthetic Recall** | **$\ge 80.0\%$** | Confirms the linear probe successfully fits diverse diffusion representations (SD 1.5, SDXL, Kandinsky) simultaneously without catastrophic forgetting of GANs. | Performance on curated benchmark samples degrades when applied to low-resolution or compressed real-world uploads. |
| **Authentic Specificity** | **$\ge 90.0\%$** | Caps false accusations on genuine photographs at $\le 10\%$. Preserves user trust on authentic images across diverse camera hardware. | A 10% false positive rate still generates 1 false alarm for every 10 real photos uploaded in production. |
| **Test ROC-AUC** | **$\ge 0.8000$** | Substantial improvement over the baseline $0.5900$, confirming meaningful class separability across threshold sweeps. | ROC-AUC does not account for real-world class imbalance (where authentic media drastically outnumbers synthetic media). |
| **CPU Inference Latency** | **$\le 900\text{ ms}$** | Preserves interactive single-image upload latency on CPU without requiring CUDA hardware acceleration. | Measures cold forward-pass latency; does not account for multi-user concurrency or API gateway overhead. |

*These gates are frozen and will serve as the acceptance criteria for Phase 16.*

---

## 7. Files Created

1. [backend/evaluation/dataset_manifest_schema.json](file:///c:/Users/PRANAV%20KARTHIKEYA/OneDrive/Desktop/T.R.A.C.E/backend/evaluation/dataset_manifest_schema.json): Formal Draft-07 JSON Schema enforcing sample IDs, licensing, SHA-256 hashes, formats, resolutions, prompts, and partition split fields.
2. [backend/evaluation/DATASET_PIPELINE.md](file:///c:/Users/PRANAV%20KARTHIKEYA/OneDrive/Desktop/T.R.A.C.E/backend/evaluation/DATASET_PIPELINE.md): Complete engineering specification for dataset audit, bias controls, held-out partitioning, training pipeline interface, and acceptance criteria.

---

*All work remains isolated within `backend/evaluation/`. Awaiting user approval before acquiring any images or executing training code.*
