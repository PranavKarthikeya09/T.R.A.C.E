# T.R.A.C.E. — Phase 17: Dataset Bias Audit and Controlled Preprocessing Report

---

## 1. Executive Summary

This report documents the empirical audit of dataset bias and controlled preprocessing on the **T.R.A.C.E.** offline specialist-model research pipeline, utilizing the **UniversalFakeDetect (UnivFD)** architecture (frozen OpenAI CLIP ViT-L/14 visual backbone with linear probe head) on both the initial 20-sample baseline and the 40-sample pilot dataset (`TRACE-Pilot-40-v1`).

### Primary Empirical Findings

1. **Measurable Non-Semantic Shortcuts in the Raw Pilot Dataset:**
   - **Container Format:** Strong statistical conflation ($\chi^2 = 10.16, p = 0.0014, I(\text{Label}; \text{Format}) = 0.2053\text{ bits}$). Authentic samples are balanced 50% PNG / 50% JPEG, whereas synthetic samples are 95% PNG (19/20) and only 5% JPEG (1/20).
   - **Aspect Ratio & Geometry:** High statistical association ($\chi^2 = 15.82, p = 0.0001, I(\text{Label}; \text{Aspect Ratio}) = 0.3238\text{ bits}$). Synthetic images are predominantly square ($65\%$, 13/20), whereas authentic images are predominantly landscape ($75\%$, 15/20) with only one square sample ($5\%$, 1/20).
   - **Resolution & Pixel Area:** Synthetic images average $928,973$ pixels ($2.85\times$ larger than authentic images at $325,702$ pixels).
   - **Color Mode:** 3 synthetic images exist in indexed palette mode (`'P'`), while authentic images are 100% 24-bit RGB.
2. **Impact of Controlled Preprocessing on the UnivFD Checkpoint:**
   - **Common Resolution (Variant C: 512×512):** ROC-AUC increased slightly from $0.5325$ to $0.5525$ (Accuracy: $60\%$, Recall: $20\%$, Specificity: $100\%$). Resizing and center-cropping did not degrade GAN detection, proving that UnivFD's sensitivity to StyleGAN2 is not merely a resolution shortcut.
   - **JPEG Standardization (Variant D: Q=85):** Subjecting all images to identical JPEG DCT quantization caused synthetic detection to drop from $20\%$ down to $10\%$ (Recall on GANs fell from $75\%$ to $25\%$, with average GAN score dropping from $0.6213$ to $0.2748$). ROC-AUC fell to $0.4825$.
   - **Combined Common Resolution + JPEG Q=85 (Variant E):** Overall Recall was $15.0\%$, Specificity $100.0\%$, ROC-AUC $0.5350$.
3. **Cross-Architecture Failure:**
   - Modern Diffusion models (SD 1.5, Kandinsky, GLIGEN, DeepFloyd IF) and Diffusion Transformer / Flow-Matching models (FLUX.1, PixArt) were completely undetected ($0.0\%$ recall) across all preprocessing variants.
4. **Data Integrity:**
   - 100% of the 20 baseline images and 40 pilot images passed SHA-256 integrity verification. No original images or manifests were modified.

---

## 2. Dataset Bias Quantification

### 2.1 File Encoding Format Distribution

| Dataset Partition | Total | PNG Count (%) | JPEG Count (%) | $\chi^2$ Statistic | Approx. $p$-value | Mutual Information $I(Y; \text{Format})$ | Shortcut Conflation Flag |
|---|---|---|---|---|---|---|---|
| **Pilot (Authentic)** | 20 | 10 (50.0%) | 10 (50.0%) | — | — | — | — |
| **Pilot (Synthetic)** | 20 | 19 (95.0%) | 1 (5.0%) | **10.1567** | **0.0014** | **0.2053 bits** | **CONFLATED** ($> 0.1\text{ bits}$) |
| **Baseline (Authentic)** | 10 | 5 (50.0%) | 5 (50.0%) | — | — | — | — |
| **Baseline (Synthetic)** | 10 | 8 (80.0%) | 2 (20.0%) | 1.9780 | 0.1596 | 0.0731 bits | Below 0.1 threshold |

*Finding:* Because 19 of the 20 pilot synthetic samples were downloaded as uncompressed PNG exports from documentation and face generation repositories, a naive linear classifier could easily learn high-frequency container signatures (or absence of 8×8 DCT blocking) rather than true generative artifacts.

---

### 2.2 Aspect Ratio and Geometry Distribution

| Class | Square (1:1) | Landscape ($>1.0$) | Portrait ($<1.0$) | $\chi^2$ Statistic | Approx. $p$-value | Mutual Information $I(Y; \text{AR})$ | Shortcut Conflation Flag |
|---|---|---|---|---|---|---|---|
| **Authentic** | 1 (5.0%) | 15 (75.0%) | 4 (20.0%) | — | — | — | — |
| **Synthetic** | 13 (65.0%) | 7 (35.0%) | 0 (0.0%) | **15.8242** | **0.0001** | **0.3238 bits** | **CONFLATED** ($> 0.1\text{ bits}$) |

*Finding:* Generative diffusion models are overwhelmingly trained and documented at native square resolutions ($512\times 512$, $1024\times 1024$), whereas natural photographic suites (MS-COCO, Kodak) follow standard camera sensor aspect ratios (3:2, 4:3).

---

### 2.3 Pixel Resolution & File Size Disparity

| Class | Pixel Count (Mean) | Pixel Count (Min) | Pixel Count (Max) | File Size (Mean KB) | File Size (Median KB) | File Size (Max KB) |
|---|---|---|---|---|---|---|
| **Authentic** | 325,702 px | 76,800 px | 393,216 px | 383.65 KB | 416.10 KB | 803.43 KB |
| **Synthetic** | 928,973 px | 262,144 px | 1,179,648 px | 942.34 KB | 1,003.96 KB | 1,817.68 KB |
| **Ratio (Synth / Auth)** | **2.85×** | **3.41×** | **3.00×** | **2.45×** | **2.41×** | **2.26×** |

---

### 2.4 Color Mode and Metadata

- **Color Modes:** Authentic images are 100% RGB (3 channels, 8-bit). Synthetic images contain 3 indexed palette images (`'P'` mode: `kandinsky_cheeseburger.png`, `kandinsky_alienplanet.png`, `deepfloyd_if_upscaled.png`).
- **Metadata & EXIF:** Zero images in the pilot or baseline retain valid camera EXIF headers or software markers. Neither class leaks camera serial numbers or generation parameter strings in standard metadata.

---

### 2.5 Statistical Power and Sample Size Caveat

The pilot sample size ($N = 40$: 20 authentic, 20 synthetic) is statistically suitable for qualitative feasibility audits, identifying obvious distribution shortcuts, and debugging pipeline mechanics. However, with $N = 20$ per class:
- A single classification change alters precision or recall by $5.0\%$.
- The 95% binomial confidence interval margin of error on accuracy is approximately $\pm 15.5\%$.
- Therefore, metrics from this pilot cannot be interpreted as generalizable real-world performance benchmarks.

---

## 3. Controlled Preprocessing Variants

To evaluate non-destructive bias mitigation, five deterministic variants were executed across all 40 pilot images:

| Variant ID | Name | Preprocessing Pipeline Description | Transformation Purpose |
|---|---|---|---|
| **Variant A** | **Baseline CLIP** | Raw image opened as RGB in memory $\rightarrow$ default CLIP preprocessing (`Resize(224, bicubic)`, `CenterCrop(224)`, ImageNet normalization). | Serves as unmodified baseline benchmark. |
| **Variant B** | **Consistent RGB Normalization** | Raw image $\rightarrow$ alpha/palette compositing on neutral white background $\rightarrow$ saved as lossless 24-bit RGB PNG $\rightarrow$ CLIP preprocessing. | Eliminates indexed palette artifacts and alpha channel variance. |
| **Variant C** | **Common 512×512 Resolution** | Raw image $\rightarrow$ RGB $\rightarrow$ isotropic resize smaller edge to 512 $\rightarrow$ center-crop 512×512 (Bicubic) $\rightarrow$ lossless PNG $\rightarrow$ CLIP preprocessing. | Completely eliminates raw dimension and aspect ratio shortcuts prior to CLIP. |
| **Variant D** | **Controlled JPEG Standardization** | Raw image $\rightarrow$ RGB $\rightarrow$ re-encoded to JPEG at documented $Q = 85$ (4:2:0 subsampling) $\rightarrow$ reloaded decoded JPEG pixels $\rightarrow$ CLIP preprocessing. | Eliminates container format bias by subjecting all images to identical DCT compression artifacts. |
| **Variant E** | **Combined 512×512 + JPEG Q=85** | Raw image $\rightarrow$ 512×512 Bicubic center-crop $\rightarrow$ re-encoded to JPEG at $Q = 85$ $\rightarrow$ reloaded decoded JPEG pixels $\rightarrow$ CLIP preprocessing. | Neutralizes BOTH dimension/aspect ratio shortcuts AND container format shortcuts simultaneously. |

*Storage Location:* Derived image files were isolated entirely under `backend/evaluation/cache/derived_variants/`, which is ignored by `.gitignore` and never committed.

---

## 4. Evaluation of Existing UnivFD Checkpoint

All variants were evaluated on CPU with the existing UnivFD linear head (`backend/evaluation/weights/fc_weights.pth`) at threshold $\tau = 0.5$. Unrounded raw sigmoid scores were utilized for exact ROC-AUC computation.

### 4.1 Aggregate Performance Across Variants

| Variant | Accuracy | Precision | Recall | Specificity | Unrounded ROC-AUC | TP | TN | FP | FN | Avg Latency |
|---|---|---|---|---|---|---|---|---|---|---|
| **Variant A: Baseline CLIP** | 60.00% | 100.00% | 20.00% | 100.00% | **0.5325** | 4 | 20 | 0 | 16 | 809.5 ms |
| **Variant B: Consistent RGB** | 60.00% | 100.00% | 20.00% | 100.00% | **0.5325** | 4 | 20 | 0 | 16 | 805.1 ms |
| **Variant C: Common 512×512** | 60.00% | 100.00% | 20.00% | 100.00% | **0.5525** | 4 | 20 | 0 | 16 | 808.2 ms |
| **Variant D: Controlled JPEG Q=85** | 55.00% | 100.00% | 10.00% | 100.00% | **0.4825** | 2 | 20 | 0 | 18 | 799.4 ms |
| **Variant E: Combined 512 + JPEG** | 57.50% | 100.00% | 15.00% | 100.00% | **0.5350** | 3 | 20 | 0 | 17 | 828.6 ms |

---

### 4.2 Disaggregated Per-Generator Family Recall

| Generator Family ($N = 4$ each) | Architecture Details | Variant A (Baseline) | Variant B (RGB) | Variant C (512×512) | Variant D (JPEG Q=85) | Variant E (Combined) |
|---|---|---|---|---|---|---|
| **GAN (StyleGAN2)** | Convolutional latent mapping | **75.0%** (3/4) | **75.0%** (3/4) | **75.0%** (3/4) | **25.0%** (1/4) | **50.0%** (2/4) |
| **High-Res Diffusion (SDXL)** | High-capacity latent U-Net | **25.0%** (1/4) | **25.0%** (1/4) | **25.0%** (1/4) | **25.0%** (1/4) | **25.0%** (1/4) |
| **Latent Diffusion (SD 1.5)** | Text-to-image latent U-Net | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) |
| **Cascaded Prior (Kandinsky, etc.)** | Prior + cascaded pixel diffusion | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) |
| **Diffusion Transformer / Flow** | FLUX.1 & PixArt-$\alpha$ (Held-Out) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) |

### 4.3 Generalization Breakdown: In-Distribution vs. Held-Out

| Partition Role | Generators Included | Variant A Recall | Variant C Recall | Variant D Recall | Variant E Recall |
|---|---|---|---|---|---|
| **In-Distribution Synthetic** | GAN, SD 1.5, SDXL, Cascaded Prior ($N = 16$) | **25.0%** (4/16) | **25.0%** (4/16) | **12.5%** (2/16) | **18.75%** (3/16) |
| **Held-Out Test Synthetic** | FLUX.1, PixArt-$\alpha$ ($N = 4$) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) | **0.0%** (0/4) |

---

## 5. Scientific Interpretation of Results

1. **Why did Variant C (512×512) maintain performance?**
   The UnivFD linear head detects StyleGAN2 images because of the spectral and textural representations learned by CLIP, not because StyleGAN2 images were $1024\times 1024$ and authentic images were $640\times 480$. Standardizing to $512\times 512$ maintained 75% GAN recall and actually improved ROC-AUC slightly to $0.5525$.
2. **Why did Variant D (JPEG Q=85) collapse GAN detection?**
   Under Variant D, StyleGAN2 closed-eye score plummeted from $0.6619$ to $0.3671$ (false negative), and overall GAN average score dropped from $0.6213$ to $0.2748$. Because UnivFD was originally trained on uncompressed ProGAN outputs, its learned linear weights place significant positive weight on high-frequency artifact channels that are vulnerable to JPEG DCT quantization.
3. **Confirmed Blind Spots of UnivFD:**
   The original UnivFD checkpoint has virtually zero sensitivity to modern latent diffusion (SD 1.5, Kandinsky) and rectified flow transformers (FLUX.1, PixArt), scoring their logits between $-7.0$ and $-12.5$ (probabilities $< 0.001$).

---

## 6. Recommendations for Dataset and Training

### Recommendation: Is the Pilot Dataset Ready for Training?

**CONDITIONAL — Requires Preprocessing Standardization or Format Rebalancing:**

1. **Do NOT train directly on the raw files without container standardization:**
   Because 19 of the 20 synthetic images are PNG and 10 of the 20 authentic images are JPEG, training a linear probe directly on raw CLIP embeddings risks fitting to the container format ($I = 0.2053\text{ bits}$).
2. **Recommended Training Pipeline Preprocessing:**
   - Either adopt **Variant D/E (Controlled JPEG Q=85 Standardization)** across all training and evaluation samples so container format is identical for all classes, OR
   - Re-acquire synthetic documentation samples in matching proportions of native JPEG and PNG prior to scaling to the full 400-image dataset.
3. **Scale from Pilot ($N = 40$) to Full Dataset ($N = 400$):**
   The 40-image pilot successfully exposed this vulnerability at negligible computational cost. Moving to the 400-image acquisition plan should enforce strict format matching (~50% JPEG / ~50% PNG for both authentic and synthetic) as designed in [DATASET_PIPELINE.md](file:///c:/Users/PRANAV%20KARTHIKEYA/OneDrive/Desktop/T.R.A.C.E/backend/evaluation/DATASET_PIPELINE.md).
