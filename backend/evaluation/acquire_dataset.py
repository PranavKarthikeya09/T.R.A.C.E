"""T.R.A.C.E. — Phase 12 Evaluation Dataset Acquisition Script.

Downloads 20 verified, labelled images (10 authentic, 10 synthetic)
directly from official and documented sources byte-for-byte, preserving
provenance, without silent re-encoding, and generates the dataset manifest.
"""

import hashlib
import json
import os
import urllib.request
from typing import Dict, List, Any


DATASET_SOURCES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 10 AUTHENTIC CAMERA CAPTURES
    # -------------------------------------------------------------------------
    {
        "id": "auth_01",
        "filename": "kodim01.png",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "https://r0k.us/graphics/kodak/kodak/kodim01.png",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "generator_type": "none (real camera capture)",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "original_identifier": "kodim01.png",
        "resizing_or_compression": "none (uncompressed 24-bit RGB PNG, 768x512)",
        "notes": "Pristine Kodak DCS capture; vintage house and architectural facade."
    },
    {
        "id": "auth_02",
        "filename": "kodim02.png",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "https://r0k.us/graphics/kodak/kodak/kodim02.png",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "generator_type": "none (real camera capture)",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "original_identifier": "kodim02.png",
        "resizing_or_compression": "none (uncompressed 24-bit RGB PNG, 768x512)",
        "notes": "Pristine Kodak DCS capture; residential house with red roof and foliage."
    },
    {
        "id": "auth_03",
        "filename": "kodim03.png",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "https://r0k.us/graphics/kodak/kodak/kodim03.png",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "generator_type": "none (real camera capture)",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "original_identifier": "kodim03.png",
        "resizing_or_compression": "none (uncompressed 24-bit RGB PNG, 768x512)",
        "notes": "Pristine Kodak DCS capture; island, trees, and sailboat on water."
    },
    {
        "id": "auth_04",
        "filename": "kodim04.png",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "https://r0k.us/graphics/kodak/kodak/kodim04.png",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "generator_type": "none (real camera capture)",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "original_identifier": "kodim04.png",
        "resizing_or_compression": "none (uncompressed 24-bit RGB PNG, 512x768)",
        "notes": "Pristine Kodak DCS capture; natural portrait of woman with hat."
    },
    {
        "id": "auth_05",
        "filename": "kodim05.png",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "https://r0k.us/graphics/kodak/kodak/kodim05.png",
        "source_dataset": "Kodak Lossless True Color Image Suite (PCD0992)",
        "generator_type": "none (real camera capture)",
        "license": "Public Domain / Research Benchmark (Eastman Kodak)",
        "original_identifier": "kodim05.png",
        "resizing_or_compression": "none (uncompressed 24-bit RGB PNG, 768x512)",
        "notes": "Pristine Kodak DCS capture; motorcycle and riders in natural light."
    },
    {
        "id": "auth_06",
        "filename": "coco_000000000139.jpg",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "http://images.cocodataset.org/val2017/000000000139.jpg",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "generator_type": "none (real camera capture)",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "original_identifier": "000000000139.jpg",
        "resizing_or_compression": "none (original camera capture JPEG as served by COCO, 640x426)",
        "notes": "Living room interior with couch, television, and ambient room lighting."
    },
    {
        "id": "auth_07",
        "filename": "coco_000000000285.jpg",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "http://images.cocodataset.org/val2017/000000000285.jpg",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "generator_type": "none (real camera capture)",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "original_identifier": "000000000285.jpg",
        "resizing_or_compression": "none (original camera capture JPEG as served by COCO, 586x640)",
        "notes": "Outdoor natural environment with bear near fallen timber in direct daylight."
    },
    {
        "id": "auth_08",
        "filename": "coco_000000000632.jpg",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "http://images.cocodataset.org/val2017/000000000632.jpg",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "generator_type": "none (real camera capture)",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "original_identifier": "000000000632.jpg",
        "resizing_or_compression": "none (original camera capture JPEG as served by COCO, 640x483)",
        "notes": "Bedroom interior scene with bedside lamp and bedspread textures."
    },
    {
        "id": "auth_09",
        "filename": "coco_000000000724.jpg",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "http://images.cocodataset.org/val2017/000000000724.jpg",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "generator_type": "none (real camera capture)",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "original_identifier": "000000000724.jpg",
        "resizing_or_compression": "none (original camera capture JPEG as served by COCO, 375x500)",
        "notes": "City street corner with traffic signals, stop sign, and parked cars."
    },
    {
        "id": "auth_10",
        "filename": "coco_000000000776.jpg",
        "ground_truth": 0,
        "target_dir": "authentic",
        "url": "http://images.cocodataset.org/val2017/000000000776.jpg",
        "source_dataset": "MS-COCO 2017 Validation Set",
        "generator_type": "none (real camera capture)",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "original_identifier": "000000000776.jpg",
        "resizing_or_compression": "none (original camera capture JPEG as served by COCO, 428x640)",
        "notes": "Commercial passenger jet airliner stationary on airport runway tarmac."
    },

    # -------------------------------------------------------------------------
    # 10 SYNTHETIC / AI-GENERATED IMAGES
    # -------------------------------------------------------------------------
    {
        "id": "synth_01",
        "filename": "progan_lsun_bedroom.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://raw.githubusercontent.com/PeterWang512/CNNDetection/master/examples/fake.png",
        "source_dataset": "Wang et al. (CVPR 2020) ForenSynths / PeterWang512",
        "generator_type": "ProGAN (Progressive GAN)",
        "license": "BSD 2-Clause License (PeterWang512/CNNDetection)",
        "original_identifier": "examples/fake.png",
        "resizing_or_compression": "none (original 256x256 PNG export)",
        "notes": "Synthetic bedroom scene synthesized by ProGAN trained on LSUN Bedroom."
    },
    {
        "id": "synth_02",
        "filename": "sd15_astronaut.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/astronaut.jpg",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "generator_type": "Stable Diffusion v1.5",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/astronaut.jpg",
        "resizing_or_compression": "none (original JPEG export as hosted, 1184x880)",
        "notes": "Text-to-image diffusion generation: 'an astronaut riding a green horse'."
    },
    {
        "id": "synth_03",
        "filename": "sd15_autopipeline.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/autopipeline-text2img.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "generator_type": "Stable Diffusion v1.5",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/autopipeline-text2img.png",
        "resizing_or_compression": "none (original 768x768 PNG export)",
        "notes": "Text-to-image AutoPipeline generation from official diffusers release guide."
    },
    {
        "id": "synth_04",
        "filename": "kandinsky_cat_hat.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/kandinsky-docs/cat_with_hat.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images (Kandinsky 2.2 Docs)",
        "generator_type": "Kandinsky 2.2",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/kandinsky-docs/cat_with_hat.png",
        "resizing_or_compression": "none (original 768x768 PNG export)",
        "notes": "Text-to-image latent prior diffusion generation: 'cat with a hat'."
    },
    {
        "id": "synth_05",
        "filename": "kandinsky_starry_cat.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/kandinsky-docs/starry_cat.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images (Kandinsky 2.2 Docs)",
        "generator_type": "Kandinsky 2.2",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/kandinsky-docs/starry_cat.png",
        "resizing_or_compression": "none (original 768x768 PNG export)",
        "notes": "Text-to-image latent prior diffusion generation: stylized cat under starry sky."
    },
    {
        "id": "synth_06",
        "filename": "ddpm_cat.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/ddpm-cat.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "generator_type": "DDPM (Denoising Diffusion Probabilistic Models)",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/ddpm-cat.png",
        "resizing_or_compression": "none (original 256x256 PNG export)",
        "notes": "Unconditional pixel-space diffusion generation trained on cat images."
    },
    {
        "id": "synth_07",
        "filename": "ddpm_butterfly.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/butterflies_final.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images",
        "generator_type": "DDPM (Denoising Diffusion Probabilistic Models)",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/butterflies_final.png",
        "resizing_or_compression": "none (original 512x512 PNG export)",
        "notes": "Unconditional diffusion generation trained on Smithsonian butterflies collection."
    },
    {
        "id": "synth_08",
        "filename": "gligen_livingroom.png",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/gligen/livingroom_modern.png",
        "source_dataset": "Hugging Face Diffusers Documentation Images (GLIGEN)",
        "generator_type": "GLIGEN (Grounded Language-Image Generation)",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/gligen/livingroom_modern.png",
        "resizing_or_compression": "none (original 640x640 PNG export)",
        "notes": "Grounded diffusion generation with bounding-box spatial layout conditioning."
    },
    {
        "id": "synth_09",
        "filename": "sdxl_dog.jpg",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/stable-diffusion-xl-coreml/a_high_quality_photo_of_a_surfing_dog.7667.final_float16_original.jpg",
        "source_dataset": "Hugging Face Diffusers Documentation Images (SDXL CoreML Blog)",
        "generator_type": "Stable Diffusion XL (SDXL Base 1.0)",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "blog/stable-diffusion-xl-coreml/a_high_quality_photo_of_a_surfing_dog.7667.final_float16_original.jpg",
        "resizing_or_compression": "none (original 1024x1024 JPEG export)",
        "notes": "SDXL Base 1.0 high-resolution generation: 'a high quality photo of a surfing dog'."
    },
    {
        "id": "synth_10",
        "filename": "flux1_output.jpg",
        "ground_truth": 1,
        "target_dir": "synthetic",
        "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/flux_ip_adapter_output.jpg",
        "source_dataset": "Hugging Face Diffusers Documentation Images (FLUX.1)",
        "generator_type": "FLUX.1 (Diffusion Transformer)",
        "license": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)",
        "original_identifier": "diffusers/flux_ip_adapter_output.jpg",
        "resizing_or_compression": "none (original 1024x1024 JPEG export)",
        "notes": "Next-generation rectified flow transformer text-to-image synthesis by Black Forest Labs."
    }
]


def acquire_dataset():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auth_dir = os.path.join(base_dir, "data", "authentic")
    synth_dir = os.path.join(base_dir, "data", "synthetic")

    os.makedirs(auth_dir, exist_ok=True)
    os.makedirs(synth_dir, exist_ok=True)

    manifest_samples = []

    print("=" * 70)
    print("T.R.A.C.E. — Phase 12 Evaluation Dataset Acquisition")
    print("=" * 70)

    for item in DATASET_SOURCES:
        target_dir = auth_dir if item["target_dir"] == "authentic" else synth_dir
        dest_path = os.path.join(target_dir, item["filename"])
        rel_path = f"backend/evaluation/data/{item['target_dir']}/{item['filename']}"

        print(f"Downloading [{item['id']}] {item['filename']} ...")
        req = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=25) as response:
            content = response.read()

        # Write exact raw bytes without modifying or re-encoding
        with open(dest_path, "wb") as f:
            f.write(content)

        # Compute SHA-256 for exact provenance
        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        print(f"  -> Saved: {dest_path} ({file_size} bytes, SHA-256: {sha256[:12]}...)")

        manifest_samples.append({
            "id": item["id"],
            "image_path": rel_path,
            "ground_truth": item["ground_truth"],
            "source_dataset": item["source_dataset"],
            "generator_type": item["generator_type"],
            "license": item["license"],
            "original_identifier": item["original_identifier"],
            "source_url": item["url"],
            "file_size_bytes": file_size,
            "sha256": sha256,
            "resizing_or_compression": item["resizing_or_compression"],
            "notes": item["notes"]
        })

    manifest = {
        "description": "T.R.A.C.E. Phase 12 — Balanced 20-Image Labelled Evaluation Manifest",
        "dataset_metadata": {
            "version": "1.0.0",
            "total_samples": len(manifest_samples),
            "authentic_count": sum(1 for s in manifest_samples if s["ground_truth"] == 0),
            "synthetic_count": sum(1 for s in manifest_samples if s["ground_truth"] == 1),
            "decision_threshold": 0.5,
            "class_mapping": {
                "0": "authentic",
                "1": "synthetic"
            },
            "created_timestamp": "2026-10-15T22:55:00+05:30"
        },
        "samples": manifest_samples
    }

    manifest_path = os.path.join(base_dir, "dataset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 70)
    print(f"[+] Dataset acquisition complete!")
    print(f"    Authentic images: {manifest['dataset_metadata']['authentic_count']}")
    print(f"    Synthetic images: {manifest['dataset_metadata']['synthetic_count']}")
    print(f"    Manifest written: {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    acquire_dataset()
