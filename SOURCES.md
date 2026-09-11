# SOURCES.md — Third-Party Models, Libraries, Datasets, and Media Assets

All third-party resources used in this project are listed below with their
license, commercial-use status, and attribution requirements.

---

## Diffusion Models (inference)

| Model | Source | License | Commercial Use | Notes |
|---|---|---|---|---|
| `stable-diffusion-xl-base-1.0` | [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | CreativeML Open RAIL++-M | No (RAIL++ terms) | Primary generation model. Revision: `462165984030d82259a11f4367a4eed129e94a7b` |
| `sdxl-vae-fp16-fix` | [madebyollin/sdxl-vae-fp16-fix](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) | Apache 2.0 | Yes | VAE for stable fp16 inference. Revision: `4df413ca49b2d5c82a85cfde3c7600551bbfc5a7` |
| `stable-diffusion-v1-5` | [runwayml/stable-diffusion-v1-5](https://huggingface.co/runwayml/stable-diffusion-v1-5) | CreativeML Open RAIL-M | No (RAIL terms) | Fallback model. Revision: `1d0c4ebf6ff58a5caecab40fa1406526bca4b5b9` |

---

## Evaluation Models (scoring only, not generation)

| Model | Source | License | Commercial Use | Notes |
|---|---|---|---|---|
| `ViT-B/32` (CLIP) | [open-clip-torch, laion2b_s34b_b79k](https://github.com/mlfoundations/open_clip) | MIT | Yes | Used for prompt adherence CLIP scoring only |
| `buffalo_l` (ArcFace) | [InsightFace](https://github.com/deepinsight/insightface) | MIT | Yes | Used for identity consistency scoring only. Never for generation. |

---

## Python Libraries

| Library | Version | License | Commercial Use |
|---|---|---|---|
| `typer` | 0.12.3 | MIT | Yes |
| `pydantic` | 2.7.4 | MIT | Yes |
| `click` | 8.1.7 | BSD-3-Clause | Yes |
| `rich` | 13.7.1 | MIT | Yes |
| `pyyaml` | 6.0.1 | MIT | Yes |
| `pillow` | 10.3.0 | HPND (PIL License) | Yes |
| `imagehash` | 4.3.1 | MIT | Yes |
| `numpy` | 1.26.4 | BSD-3-Clause | Yes |
| `torch` | 2.3.1 | BSD-3-Clause | Yes |
| `open-clip-torch` | 2.24.0 | MIT | Yes |
| `diffusers` | 0.29.2 | Apache 2.0 | Yes |
| `transformers` | 4.42.3 | Apache 2.0 | Yes |
| `accelerate` | 0.31.0 | Apache 2.0 | Yes |
| `pytest` | 8.2.2 | MIT | Yes |
| `pytest-cov` | 5.0.0 | MIT | Yes |

---

## Compute Infrastructure

| Resource | Provider | Cost | Notes |
|---|---|---|---|
| Kaggle Notebooks (T4 GPU) | Google/Kaggle | Free (30h/week) | Used for SDXL inference only |
| Local CPU | Developer machine | Free | All other pipeline steps |

No paid APIs, no credit card, no proprietary generation services were used.

---

## Datasets

No datasets were used directly. The SDXL model was pre-trained by Stability AI
on LAION-5B (see Stability AI's model card for full dataset disclosure).

---

## Attribution Requirements

- `stable-diffusion-xl-base-1.0`: Per CreativeML RAIL++-M, outputs must not
  claim to be real photographs of real people. The `synthetic_media_label: true`
  field in every `avatar_manifest.json` satisfies this requirement.
- `open-clip`: MIT license, no special attribution required beyond this listing.
- `InsightFace buffalo_l`: MIT license, no special attribution required.
