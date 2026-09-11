# Technical Report — avatarpipe PS02

## Architecture

The pipeline is split into two strict execution environments:

**CPU (local laptop) — all logic:**
- `spec.py`: AvatarSpec schema with Pydantic v2 validation
- `safety.py`: rule-based content policy (blocklist + flag rules)
- `job_builder.py`: spec -> portable JSON job bundle
- `cli.py`: Typer CLI with 6 subcommands
- `output_validator.py`: image corruption/dimension/hash checks
- `manifest.py`: avatar_manifest.json writer
- `evaluation/`: CLIP adherence, diversity coverage, identity consistency
- `consent.py`: consent record management (Exceptional)
- `tests/`: 92 tests, all run without a GPU

**GPU (Kaggle T4 notebook) — inference only:**
- `notebooks/inference_kaggle.ipynb`: SDXL-base-1.0 diffusion inference

This split ensures: (a) all business logic is testable without a GPU,
(b) the expensive step is clearly isolated and auditable, and (c) the
CPU side can be iterated on freely without burning accelerator quota.

## Model Choice

**Primary: `stabilityai/stable-diffusion-xl-base-1.0`**
- Rationale: highest quality open-weight text-to-image model that fits
  in Kaggle T4 (16GB VRAM) without quantization
- Revision pinned to `462165984030d82259a11f4367a4eed129e94a7b`
- Fallback: `runwayml/stable-diffusion-v1-5` for lower-VRAM environments

**Alternatives considered:**
- SD-Turbo: faster (1-4 steps) but lower quality for portrait work
- DALL-E 3: proprietary API, violates constraint §0.2
- Midjourney: proprietary, violates constraint §0.2
- Flux.1-dev: excellent quality but requires ~24GB VRAM, exceeds Kaggle T4

## Safety Architecture

Three-level severity system (clean/flag/block):
- **Block**: hard refusal + logged reason (explicit content, real-person deepfake, violence, CSAM, harmful instructions)
- **Flag**: allow but warn (under-specified fields, contradictory attire/background, all-caps input)
- **Clean**: pass-through

Every result is written to avatar_manifest.json regardless of severity.
Rules are regex-based + auditable -- no black-box ML classifier as primary gate.

## Diversity Design

The NO nationality/ethnicity field decision is enforced at the schema level
(not a runtime check) because:
1. Schema-level enforcement is the earliest possible intervention
2. It prevents category from existing in any job bundle or manifest
3. Skin tone uses Fitzpatrick scale (I-VI) -- a dermatological descriptor
   with no implied nationality or genetic claim

## Failure Cases Encountered

1. `setuptools.backends.legacy:build` -- incorrect pyproject.toml backend
   name; fixed to `setuptools.build_meta`
2. Empty consent_id validation -- the first validator caught `not ""` before
   the second check; fixed by restructuring the validator to check None vs
   empty string separately
3. Solid-colour test image failing non-blank check -- expected; the validator
   is correct (zero variance = degenerate). Fixed test to use noise image.

## Production Recommendations

To go from assessment code to a real internal tool:
1. **Async job queue**: replace file-based job bundles with a message queue
   (Celery + Redis) for concurrent generation requests
2. **Consent DB**: replace file-based consent store with PostgreSQL + audit log
3. **Output CDN**: store images in object storage (S3-compatible), not local paths
4. **Model versioning**: current pinning is per-project; production needs a
   model registry service with rollback capability
5. **RAIL++ license review**: SDXL is not commercially licensed without a
   Stability AI enterprise agreement; for commercial use, evaluate Flux-1.0-schnell
   (Apache 2.0) or a licensed SDXL variant
6. **Privacy review**: even with synthetic avatars, output images may be used
   to train downstream models; require explicit opt-in for any such use case
