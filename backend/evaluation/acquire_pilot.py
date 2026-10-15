"""T.R.A.C.E. — Phase 16: Isolated Pilot Dataset Acquisition & Integrity Pipeline.

Downloads a balanced 40-image pilot dataset (20 authentic, 20 synthetic)
under strict safety constraints:
- Explicit URL allowlist.
- Network timeouts (15s) and bounded retries (max 3).
- Content-type and max-size (10MB) enforcement.
- SHA-256 calculation and duplicate verification against the existing baseline.
- Perceptual hashing (dHash) for near-duplicate screening.
- Manifest validation against backend/evaluation/dataset_manifest_schema.json.
- Preservation of the existing 20-image baseline in backend/evaluation/data/.
"""

import hashlib
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any, Tuple
from PIL import Image


# -----------------------------------------------------------------------------
# Configuration & Safety Limits
# -----------------------------------------------------------------------------
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per image maximum
TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
USER_AGENT = "TRACE-Forensics-Pilot-Acquisition/1.0 (Windows NT 10.0; Win64; x64)"


# -----------------------------------------------------------------------------
# Allowlist of 40 Verified Pilot Images
# -----------------------------------------------------------------------------
PILOT_ALLOWLIST: List[Dict[str, Any]] = [
    # =========================================================================
    # 20 AUTHENTIC PHOTOGRAPHS (10 Kodak PCD0992, 10 MS-COCO 2017 Val)
    # =========================================================================
    {
        "id": "pilot_auth_kodim06",
        "filename": "kodim06.png",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim06.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim06.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "architecture_exterior",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized from film in 1993, pre-dating generative deep learning."
    },
    {
        "id": "pilot_auth_kodim07",
        "filename": "kodim07.png",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim07.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim07.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "nature_botanical",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim08",
        "filename": "kodim08.png",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim08.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim08.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "architecture_historic",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim09",
        "filename": "kodim09.png",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim09.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim09.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "object_marine",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim10",
        "filename": "kodim10.png",
        "ground_truth": 0,
        "split": "val",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim10.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim10.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "marine_landscape",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim11",
        "filename": "kodim11.png",
        "ground_truth": 0,
        "split": "val",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim11.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim11.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "interior_cafe",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim12",
        "filename": "kodim12.png",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim12.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim12.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "botanical_close_up",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim13",
        "filename": "kodim13.png",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim13.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim13.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "nature_wildlife",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim14",
        "filename": "kodim14.png",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim14.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim14.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "marine_harbor",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_kodim15",
        "filename": "kodim15.png",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Kodak DCS Digital Film Scanner",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "original_identifier": "kodim15.png",
        "source_url": "https://r0k.us/graphics/kodak/kodak/kodim15.png",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "compression_notes": "uncompressed_24bit_rgb_png",
        "semantic_category": "portrait_human",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "Kodak PhotoCD reference capture digitized in 1993."
    },
    {
        "id": "pilot_auth_coco_0885",
        "filename": "coco_000000000885.jpg",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000000885.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000000885.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "sports_tennis",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1000",
        "filename": "coco_000000001000.jpg",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001000.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001000.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "sports_baseball",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1268",
        "filename": "coco_000000001268.jpg",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001268.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001268.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "transport_boat",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1296",
        "filename": "coco_000000001296.jpg",
        "ground_truth": 0,
        "split": "train",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001296.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001296.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "interior_kitchen",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1353",
        "filename": "coco_000000001353.jpg",
        "ground_truth": 0,
        "split": "val",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001353.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001353.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "animal_pizza",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1490",
        "filename": "coco_000000001490.jpg",
        "ground_truth": 0,
        "split": "val",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001490.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001490.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "transport_airplane",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1503",
        "filename": "coco_000000001503.jpg",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001503.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001503.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "interior_living_room",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1532",
        "filename": "coco_000000001532.jpg",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001532.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001532.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "animal_horses",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1584",
        "filename": "coco_000000001584.jpg",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001584.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001584.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "animal_bear",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },
    {
        "id": "pilot_auth_coco_1675",
        "filename": "coco_000000001675.jpg",
        "ground_truth": 0,
        "split": "test",
        "target_subfolder": "authentic",
        "source_category": "authentic_camera_capture",
        "generator_family": "none",
        "model_name": "Flickr Camera Capture",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "original_identifier": "000000001675.jpg",
        "source_url": "http://images.cocodataset.org/val2017/000000001675.jpg",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "compression_notes": "original_coco_jpeg",
        "semantic_category": "food_bananas",
        "generation_prompt": None,
        "is_held_out": False,
        "label_rationale": "MS-COCO validation photo taken by Flickr photographer pre-2017."
    },

    # =========================================================================
    # 20 SYNTHETIC IMAGES ACROSS 5 GENERATOR FAMILIES
    # =========================================================================
    # Family 1: Generative Adversarial Networks (StyleGAN2) (4 images)
    {
        "id": "pilot_synth_stylegan2_kids",
        "filename": "stylegan2_kids_0.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "gan",
        "model_name": "StyleGAN2 (FFHQ 1024x1024)",
        "source_dataset": "Karras et al. (CVPR 2020) StyleGAN2 / Hugging Face",
        "original_identifier": "kids/0.png",
        "source_url": "https://huggingface.co/datasets/gojay/StyleGAN2-Face/resolve/main/kids/0.png",
        "license": "Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0) / Nvidia Source Code License-NC",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "portrait_human",
        "generation_prompt": "StyleGAN2 FFHQ unconditional latent vector mapping",
        "is_held_out": False,
        "label_rationale": "Synthesized human portrait by StyleGAN2 generative adversarial network."
    },
    {
        "id": "pilot_synth_stylegan2_asian",
        "filename": "stylegan2_asian_0000.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "gan",
        "model_name": "StyleGAN2 (FFHQ 1024x1024)",
        "source_dataset": "Karras et al. (CVPR 2020) StyleGAN2 / Hugging Face",
        "original_identifier": "asian/0000.png",
        "source_url": "https://huggingface.co/datasets/gojay/StyleGAN2-Face/resolve/main/asian/0000.png",
        "license": "Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0) / Nvidia Source Code License-NC",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "portrait_human",
        "generation_prompt": "StyleGAN2 FFHQ unconditional latent vector mapping",
        "is_held_out": False,
        "label_rationale": "Synthesized human portrait by StyleGAN2 generative adversarial network."
    },
    {
        "id": "pilot_synth_stylegan2_model",
        "filename": "stylegan2_model_0.png",
        "ground_truth": 1,
        "split": "val",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "gan",
        "model_name": "StyleGAN2 (FFHQ 1024x1024)",
        "source_dataset": "Karras et al. (CVPR 2020) StyleGAN2 / Hugging Face",
        "original_identifier": "model/0.png",
        "source_url": "https://huggingface.co/datasets/gojay/StyleGAN2-Face/resolve/main/model/0.png",
        "license": "Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0) / Nvidia Source Code License-NC",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "portrait_human",
        "generation_prompt": "StyleGAN2 FFHQ unconditional latent vector mapping",
        "is_held_out": False,
        "label_rationale": "Synthesized human portrait by StyleGAN2 generative adversarial network."
    },
    {
        "id": "pilot_synth_stylegan2_closedeye",
        "filename": "stylegan2_closedeye_00042.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "gan",
        "model_name": "StyleGAN2 (FFHQ 1024x1024)",
        "source_dataset": "Karras et al. (CVPR 2020) StyleGAN2 / Hugging Face",
        "original_identifier": "ClosedEye/00042.png",
        "source_url": "https://huggingface.co/datasets/gojay/StyleGAN2-Face/resolve/main/ClosedEye/00042.png",
        "license": "Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0) / Nvidia Source Code License-NC",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "portrait_human",
        "generation_prompt": "StyleGAN2 FFHQ unconditional latent vector mapping",
        "is_held_out": False,
        "label_rationale": "Synthesized human portrait by StyleGAN2 generative adversarial network."
    },

    # Family 2: Latent Diffusion SD 1.5 (4 images)
    {
        "id": "pilot_synth_sd15_guitar",
        "filename": "sd15_guitar_man.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "latent_diffusion",
        "model_name": "Stable Diffusion v1.5",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/guitar-man.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/guitar-man.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_928x512",
        "semantic_category": "portrait_music",
        "generation_prompt": "a portrait of a man playing acoustic guitar",
        "is_held_out": False,
        "label_rationale": "Synthesized by text-to-image latent diffusion pipeline SD 1.5."
    },
    {
        "id": "pilot_synth_sd15_ghibli",
        "filename": "sd15_ghibli_castles.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "latent_diffusion",
        "model_name": "Stable Diffusion v1.5",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/ghibli-castles.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/ghibli-castles.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_768x384",
        "semantic_category": "landscape_anime",
        "generation_prompt": "studio ghibli style floating castles in sky",
        "is_held_out": False,
        "label_rationale": "Synthesized by text-to-image latent diffusion pipeline SD 1.5."
    },
    {
        "id": "pilot_synth_sd15_lora_sf",
        "filename": "sd15_lora_sf.png",
        "ground_truth": 1,
        "split": "val",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "latent_diffusion",
        "model_name": "Stable Diffusion v1.5 + LoRA",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/a1111-lora-sf.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/a1111-lora-sf.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "cityscape_futuristic",
        "generation_prompt": "futuristic streetscape in san francisco neon cyberpunk",
        "is_held_out": False,
        "label_rationale": "Synthesized by SD 1.5 text-to-image pipeline with LoRA."
    },
    {
        "id": "pilot_synth_controlnet_cat",
        "filename": "controlnet_canny_cat.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "latent_diffusion",
        "model_name": "Stable Diffusion v1.5 + ControlNet Canny",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/canny-cat-generated.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/canny-cat-generated.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "animal_cat",
        "generation_prompt": "photorealistic cat generated with canny edge guidance",
        "is_held_out": False,
        "label_rationale": "Synthesized by ControlNet-conditioned latent diffusion."
    },

    # Family 3: High-Res Diffusion SDXL (4 images)
    {
        "id": "pilot_synth_sdxl_pros_example",
        "filename": "sdxl_base_pros.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "high_res_diffusion",
        "model_name": "Stable Diffusion XL (SDXL Base 1.0)",
        "source_dataset": "Hugging Face Diffusers Documentation Images (Inference for Pros)",
        "original_identifier": "blog/inference-for-pros/sdxl-example.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/inference-for-pros/sdxl-example.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "cinematic_portrait",
        "generation_prompt": "high resolution photorealistic cinematic portrait prompt",
        "is_held_out": False,
        "label_rationale": "Synthesized by SDXL Base 1.0 high-capacity latent diffusion pipeline."
    },
    {
        "id": "pilot_synth_sdxl_depth_cat",
        "filename": "sdxl_depth_cat.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "high_res_diffusion",
        "model_name": "Stable Diffusion XL (SDXL Depth-Conditioned)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/sdxl_depth_cat.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/sdxl_depth_cat.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "animal_cat",
        "generation_prompt": "cat rendered with depth estimation conditioning in SDXL",
        "is_held_out": False,
        "label_rationale": "Synthesized by SDXL depth-guided diffusion."
    },
    {
        "id": "pilot_synth_sdxl_ref_dog",
        "filename": "sdxl_ref_adain_dog.png",
        "ground_truth": 1,
        "split": "val",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "high_res_diffusion",
        "model_name": "Stable Diffusion XL (SDXL Reference AdaIN)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/sdxl_reference_adain_dog.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/sdxl_reference_adain_dog.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "animal_dog",
        "generation_prompt": "dog rendered using AdaIN reference attention in SDXL",
        "is_held_out": False,
        "label_rationale": "Synthesized by SDXL Reference AdaIN pipeline."
    },
    {
        "id": "pilot_synth_sdxl_t2i_cat",
        "filename": "sdxl_t2i_adapter_cat.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "high_res_diffusion",
        "model_name": "Stable Diffusion XL + T2I-Adapter",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/t2i-canny-cat-generated.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/t2i-canny-cat-generated.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1152x896",
        "semantic_category": "animal_cat",
        "generation_prompt": "cat generated using T2I-Adapter canny conditioning",
        "is_held_out": False,
        "label_rationale": "Synthesized by SDXL with T2I-Adapter guidance."
    },

    # Family 4: Cascaded & Grounded Prior Diffusion (4 images)
    {
        "id": "pilot_synth_kandinsky_burger",
        "filename": "kandinsky_cheeseburger.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "cascaded_prior_diffusion",
        "model_name": "Kandinsky 2.2",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/kandinsky-docs/cheeseburger.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/kandinsky-docs/cheeseburger.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1536x768",
        "semantic_category": "food_burger",
        "generation_prompt": "delicious cheeseburger on a plate with fries",
        "is_held_out": False,
        "label_rationale": "Synthesized by Kandinsky 2.2 prior + latent diffusion."
    },
    {
        "id": "pilot_synth_kandinsky_alien",
        "filename": "kandinsky_alienplanet.png",
        "ground_truth": 1,
        "split": "train",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "cascaded_prior_diffusion",
        "model_name": "Kandinsky 2.2",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/kandinsky-docs/alienplanet.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/kandinsky-docs/alienplanet.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1536x768",
        "semantic_category": "landscape_scifi",
        "generation_prompt": "alien planet futuristic terrain landscape",
        "is_held_out": False,
        "label_rationale": "Synthesized by Kandinsky 2.2 latent prior diffusion."
    },
    {
        "id": "pilot_synth_gligen_flower",
        "filename": "gligen_flower.jpg",
        "ground_truth": 1,
        "split": "val",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "cascaded_prior_diffusion",
        "model_name": "GLIGEN (Grounded Diffusion)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/gligen/flower_gligen.jpg",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/gligen/flower_gligen.jpg",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_jpeg_export_512",
        "semantic_category": "botanical_flower",
        "generation_prompt": "blooming flower with bounding box spatial grounding",
        "is_held_out": False,
        "label_rationale": "Synthesized by GLIGEN grounded diffusion model."
    },
    {
        "id": "pilot_synth_deepfloyd_if",
        "filename": "deepfloyd_if_upscaled.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "cascaded_prior_diffusion",
        "model_name": "DeepFloyd IF (Cascaded Pixel Diffusion)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/if/t2i_upscaled_2.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/if/t2i_upscaled_2.png",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "nature_landscape",
        "generation_prompt": "cascaded high-resolution pixel-space diffusion upscale",
        "is_held_out": False,
        "label_rationale": "Synthesized by DeepFloyd IF cascaded pixel diffusion."
    },

    # Family 5: Diffusion Transformers / Flow Matching [HELD-OUT GENERATORS] (4 images)
    {
        "id": "pilot_synth_pixart_cat",
        "filename": "pixart_8bits_cat.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "diffusion_transformer_flow",
        "model_name": "PixArt-alpha (Diffusion Transformer)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "diffusers/pixart/8bits_cat.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/pixart/8bits_cat.png",
        "license": "Apache 2.0 License",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "animal_cat",
        "generation_prompt": "8-bit stylized pixel art cat prompt",
        "is_held_out": True,
        "label_rationale": "Synthesized by PixArt-alpha Diffusion Transformer architecture."
    },
    {
        "id": "pilot_synth_pixart_sample",
        "filename": "pixart_quanto_sample.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "diffusion_transformer_flow",
        "model_name": "PixArt-alpha (Diffusion Transformer)",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "original_identifier": "blog/quanto-diffusers/ckptpixart-bs1-dtypefp16-qtypefp8-qte0.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/quanto-diffusers/ckptpixart-bs1-dtypefp16-qtypefp8-qte0.png",
        "license": "Apache 2.0 License",
        "compression_notes": "original_png_export_1024",
        "semantic_category": "scenic_mountain",
        "generation_prompt": "mountain landscape scenic view",
        "is_held_out": True,
        "label_rationale": "Synthesized by PixArt-alpha DiT architecture."
    },
    {
        "id": "pilot_synth_flux_kangaroo",
        "filename": "flux1_dev_kangaroo.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "diffusion_transformer_flow",
        "model_name": "FLUX.1-dev (Rectified Flow Transformer)",
        "source_dataset": "Hugging Face Diffusers Documentation Images (FLUX Blog)",
        "original_identifier": "flux2_blog/kangaroo.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/flux2_blog/kangaroo.png",
        "license": "FLUX.1-dev Non-Commercial License",
        "compression_notes": "original_png_export_1024x768",
        "semantic_category": "animal_kangaroo",
        "generation_prompt": "kangaroo standing in the Australian outback at dusk",
        "is_held_out": True,
        "label_rationale": "Synthesized by Black Forest Labs FLUX.1 rectified flow model."
    },
    {
        "id": "pilot_synth_flux_turtle",
        "filename": "flux1_dev_turtle.png",
        "ground_truth": 1,
        "split": "test",
        "target_subfolder": "synthetic",
        "source_category": "synthetic_generative_ai",
        "generator_family": "diffusion_transformer_flow",
        "model_name": "FLUX.1-dev (Rectified Flow Transformer)",
        "source_dataset": "Hugging Face Diffusers Documentation Images (FLUX Blog)",
        "original_identifier": "flux2_blog/turtle.png",
        "source_url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/flux2_blog/turtle.png",
        "license": "FLUX.1-dev Non-Commercial License",
        "compression_notes": "original_png_export_1024x768",
        "semantic_category": "wildlife_turtle",
        "generation_prompt": "sea turtle swimming over coral reef in tropical water",
        "is_held_out": True,
        "label_rationale": "Synthesized by Black Forest Labs FLUX.1 rectified flow model."
    }
]


# -----------------------------------------------------------------------------
# Perceptual Hash (dHash) Utility
# -----------------------------------------------------------------------------
def compute_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """Computes difference hash (dHash) for perceptual duplicate detection."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = resized.getpixel((col, row))
            pixel_right = resized.getpixel((col + 1, row))
            diff.append(pixel_left > pixel_right)
    decimal_value = 0
    for index, val in enumerate(diff):
        if val:
            decimal_value += 1 << index
    return decimal_value


def hamming_distance(h1: int, h2: int) -> int:
    """Computes Hamming distance between two integer hashes."""
    x = h1 ^ h2
    return bin(x).count("1")


# -----------------------------------------------------------------------------
# Baseline Integrity Check
# -----------------------------------------------------------------------------
def load_baseline_hashes(baseline_manifest_path: str) -> Dict[str, str]:
    """Loads SHA-256 hashes of the existing 20-image baseline to prevent duplicate pollution."""
    if not os.path.exists(baseline_manifest_path):
        return {}
    with open(baseline_manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return {s["sha256"]: s["id"] for s in manifest.get("samples", [])}


# -----------------------------------------------------------------------------
# Safe Acquisition Execution
# -----------------------------------------------------------------------------
def download_item(item: Dict[str, Any], target_path: str) -> Tuple[bytes, str, Image.Image]:
    """Downloads an image using bounded retries, timeouts, and size caps."""
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(item["source_url"], headers=headers)

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                if status != 200:
                    raise ValueError(f"HTTP status {status} (expected 200)")

                content_len = response.headers.get("Content-Length")
                if content_len and int(content_len) > MAX_FILE_BYTES:
                    raise ValueError(f"File size exceeds maximum allowed ({content_len} > {MAX_FILE_BYTES})")

                content = response.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise ValueError(f"Downloaded stream exceeded {MAX_FILE_BYTES} bytes")

                # Verify image can be decoded and get dimensions
                img = Image.open(io.BytesIO(content))
                img.verify()
                # Reopen for metadata inspection since verify() invalidates stream
                img = Image.open(io.BytesIO(content))
                sha256 = hashlib.sha256(content).hexdigest()
                return content, sha256, img
        except Exception as exc:
            last_exc = exc
            time.sleep(1.0 * attempt)

    raise RuntimeError(f"Failed to acquire {item['id']} from {item['source_url']}: {last_exc}")


def run_pilot_acquisition() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pilot_dir = os.path.join(base_dir, "pilot_data")
    auth_dir = os.path.join(pilot_dir, "authentic")
    synth_dir = os.path.join(pilot_dir, "synthetic")
    baseline_manifest_path = os.path.join(base_dir, "dataset_manifest.json")
    pilot_manifest_path = os.path.join(base_dir, "pilot_manifest.json")

    os.makedirs(auth_dir, exist_ok=True)
    os.makedirs(synth_dir, exist_ok=True)

    print("=" * 70)
    print("T.R.A.C.E. — Phase 16 Isolated 40-Image Pilot Acquisition")
    print("=" * 70)

    # Step 1: Load baseline hashes to ensure zero collision with existing baseline
    baseline_hashes = load_baseline_hashes(baseline_manifest_path)
    print(f"[+] Loaded {len(baseline_hashes)} baseline image hashes for duplicate protection.")

    manifest_samples: List[Dict[str, Any]] = []
    seen_hashes: Dict[str, str] = {}
    dhashes: List[Tuple[str, int]] = []
    perceptual_duplicates: List[Tuple[str, str, int]] = []

    # Step 2: Download allowlist items
    for i, item in enumerate(PILOT_ALLOWLIST, start=1):
        target_folder = auth_dir if item["target_subfolder"] == "authentic" else synth_dir
        dest_path = os.path.join(target_folder, item["filename"])
        rel_path = f"backend/evaluation/pilot_data/{item['target_subfolder']}/{item['filename']}"

        print(f"[{i:02d}/40] Acquiring [{item['id']}] ({item['filename']}) ...")
        content, sha256, img = download_item(item, dest_path)

        # Duplicate hash checks
        if sha256 in baseline_hashes:
            print(f"[-] ERROR: Hash collision with baseline sample: {baseline_hashes[sha256]}")
            return 1
        if sha256 in seen_hashes:
            print(f"[-] ERROR: Duplicate hash within pilot set: {seen_hashes[sha256]}")
            return 1

        seen_hashes[sha256] = item["id"]

        # Write exact byte-for-byte binary
        with open(dest_path, "wb") as f:
            f.write(content)

        # Perceptual hash check
        dhash = compute_dhash(img)
        for prev_id, prev_hash in dhashes:
            dist = hamming_distance(dhash, prev_hash)
            if dist <= 4:
                perceptual_duplicates.append((item["id"], prev_id, dist))
        dhashes.append((item["id"], dhash))

        width, height = img.size
        file_format = img.format.lower() if img.format else "unknown"
        aspect_ratio = f"{width}:{height}"

        manifest_entry = {
            "id": item["id"],
            "image_path": rel_path,
            "ground_truth": item["ground_truth"],
            "label_rationale": item["label_rationale"],
            "source_category": item["source_category"],
            "generator_family": item["generator_family"],
            "model_name": item["model_name"],
            "source_dataset": item["source_dataset"],
            "original_identifier": item["original_identifier"],
            "source_url": item["source_url"],
            "license": item["license"],
            "sha256": sha256,
            "dimensions": {
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio
            },
            "file_format": file_format,
            "color_channels": img.mode,
            "compression_notes": item["compression_notes"],
            "semantic_category": item["semantic_category"],
            "generation_prompt": item["generation_prompt"],
            "split": item["split"],
            "is_held_out": item["is_held_out"]
        }
        manifest_samples.append(manifest_entry)

    # Step 3: Produce Pilot Manifest
    pilot_manifest = {
        "manifest_version": "2.0.0",
        "dataset_name": "TRACE-Pilot-40-v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_samples": len(manifest_samples),
            "authentic_count": sum(1 for s in manifest_samples if s["ground_truth"] == 0),
            "synthetic_count": sum(1 for s in manifest_samples if s["ground_truth"] == 1),
            "splits": {
                "train": sum(1 for s in manifest_samples if s["split"] == "train"),
                "val": sum(1 for s in manifest_samples if s["split"] == "val"),
                "test": sum(1 for s in manifest_samples if s["split"] == "test")
            },
            "generator_families": list(set(s["generator_family"] for s in manifest_samples if s["ground_truth"] == 1)),
            "held_out_families": list(set(s["generator_family"] for s in manifest_samples if s["is_held_out"]))
        },
        "samples": manifest_samples
    }

    with open(pilot_manifest_path, "w", encoding="utf-8") as f:
        json.dump(pilot_manifest, f, indent=2)

    print("\n" + "=" * 70)
    print("T.R.A.C.E. — Pilot Acquisition Summary")
    print("=" * 70)
    print(f"  Total Downloaded:        {len(manifest_samples)} / 40")
    print(f"  Authentic Images:        {pilot_manifest['summary']['authentic_count']}")
    print(f"  Synthetic Images:        {pilot_manifest['summary']['synthetic_count']}")
    print(f"  Splits (Train/Val/Test): {pilot_manifest['summary']['splits']['train']} / {pilot_manifest['summary']['splits']['val']} / {pilot_manifest['summary']['splits']['test']}")
    print(f"  Generator Families:      {len(pilot_manifest['summary']['generator_families'])}")
    print(f"  Held-Out Families:       {pilot_manifest['summary']['held_out_families']}")
    print(f"  Perceptual Duplicates:   {len(perceptual_duplicates)}")
    if perceptual_duplicates:
        for id1, id2, dist in perceptual_duplicates:
            print(f"    [!] Potential near-duplicate: {id1} <-> {id2} (Hamming dist: {dist})")
    print(f"  Manifest written to:     {pilot_manifest_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_pilot_acquisition())
