# PS02 Official Workbook Completion Guide

This document contains the exact data and responses required to complete the official PS02 candidate workbook across all sheets (`00_START` through `07_BATCH_MODERATION`).

---

## Sheet: `00_START`
- **Candidate Name:** [Your Name]
- **Assessment Track:** PS02 — Open-Source AI Human-Avatar Generation
- **Target Tier:** Exceptional
- **Operating System:** Windows 11 (64-bit) / Cross-platform compatible
- **Python Version:** 3.12.10 (tested with virtualenv / Conda `avatarpipe` Python 3.10+)
- **Local Compute Hardware:** CPU only (Intel/AMD x86_64, 16GB RAM)
- **Accelerator Compute Provider:** Kaggle Notebooks (Free Tier — NVIDIA T4, 16GB VRAM, 30h/week quota)
- **Primary Model Checkpoint:** `stabilityai/stable-diffusion-xl-base-1.0`
  - HF Commit Hash: `462165984030d82259a11f4367a4eed129e94a7b`
- **VAE Checkpoint:** `madebyollin/sdxl-vae-fp16-fix`
  - HF Commit Hash: `4df413ca49b2d5c82a85cfde3c7600551bbfc5a7`
- **Identity Scoring Model:** `buffalo_l` (InsightFace ArcFace, MIT License)
- **Prompt Adherence Model:** `ViT-B-32` (`laion2b_s34b_b79k` via `open-clip-torch`, MIT License)
- **Repository Link:** (Local / Git workspace)
- **Total Automated Test Count:** 98 tests (100% passing)

---

## Sheet: `01_SYSTEM_ARCHITECTURE`
- **Architectural Paradigm:** Clean Two-Tier Separation (Local CPU Orchestration + Remote Accelerator Inference).
- **CPU Responsibilities:** CLI interface (`Typer`), schema validation (`Pydantic v2`), rule-based safety screening, job bundling, image corruption detection, SHA256 provenance calculation, manifest generation, diversity & identity metric computation, unit/integration testing.
- **GPU Responsibilities:** Pinned diffusion inference only (`StableDiffusionXLPipeline` with FP16 VAE fix and attention slicing).
- **Prohibited Infrastructure:** Google Colab is strictly excluded (policy compliance). No commercial or paid generation APIs.
- **Data Contract:** Flat JSON portable job bundle (`jobs/<uuid>.json`) containing full spec, resolved prompts, negative prompt, seed, model revisions, and provenance route.

---

## Sheet: `02_SPEC_AND_PROMPT_ENGINEERING`
- **Attribute Neutrality:** Strictly eliminates `nationality` and `ethnicity` fields. Appearance attributes (`skin_tone`, `hair`, `attire`, `background`, `pose`) are decoupled, independent parameters.
- **Skin Tone Representation:** Fitzpatrick scale (I through VI) and neutral dermatological descriptors.
- **Seed Handling:** Deterministic 32-bit integer automatically generated via `secrets.randbits(32)` if null, ensuring cryptographic unpredictability prior to assignment while guaranteeing 100% bitwise reproducibility once recorded.
- **Prompt Formulation:** Token sequence structured for cross-attention priority:
  `[Subject: age + presentation + skin_tone + hair] -> [Attire] -> [Pose] -> [Environment/Background] -> [Studio photographic quality qualifiers]`.

---

## Sheet: `03_SAFETY_AND_ETHICS`
- **Policy Engine:** `src/avatarpipe/safety.py`
- **Severity Levels:**
  - `clean`: No triggers; permitted with full audit logging.
  - `flag`: Under-specified descriptors or climatically contradictory attire/background pairs. Permitted with warning flag logged to manifest.
  - `block`: Immediate hard refusal (explicit sexual/NSFW, CSAM, unauthorized real-person deepfakes, weapons/explosive instructions, graphic violence).
- **Synthetic Media Disclosure:** `synthetic_media_label: true` is unconditionally enforced in every `avatar_manifest.json` per CreativeML Open RAIL++-M obligations.

---

## Sheet: `04_CONSENT_MANAGEMENT (Exceptional Tier)`
- **Consent Gate:** `src/avatarpipe/consent.py`
- **Enforcement:** `AvatarSpec` schema validator throws immediate `ValidationError` if `reference_images` is populated without a valid `consent_id`.
- **Right to Erasure (GDPR):** `ConsentStore.delete_artifacts(consent_id)` purges all generated files associated with a revoked consent record from storage.
- **Audit Records:** Stored as independent JSON records under `consent_store/<consent_id>.json`.

---

## Sheet: `05_BENCHMARK_AND_PERFORMANCE`
*(Values taken from live benchmark run on developer machine)*
- **Spec Validation Latency:** ~0.003 ms / validation
- **Safety Screening Latency:** ~0.074 ms / screening
- **CPU Pipeline Mean Execution Time:** 0.189 seconds / job
- **Job Success Rate:** 100% (5/5 clean benchmark cycles)
- **Peak Local RAM Overhead:** 8.9 MB
- **GPU Inference Latency (Kaggle T4):** ~12–16 seconds for 1024x1024 SDXL at 20 steps (FP16)
- **Test Suite Execution Time:** 98 tests in 3.68 seconds

---

## Sheet: `06_EVIDENCE_INDEX`
- **Baseline Six Avatars:** `evidence/test_matrix/baseline_six/`
- **Attribute Isolation Suite:** `evidence/test_matrix/attribute_isolation/`
- **Ambiguous Input Test:** `evidence/test_matrix/ambiguous/ambiguous_result.json`
- **Unsafe Request Refusal:** `evidence/test_matrix/unsafe_refusal/refusal_log.json`
- **Corrupted Image Handling:** `evidence/test_matrix/corrupted/validation_failure_report.json`
- **Consented 10-Image Matrix:** `evidence/test_matrix/consented_persona/`

---

## Sheet: `07_BATCH_MODERATION`
- **Adherence Scoring:** Cosine similarity via `open-clip-torch` (ViT-B-32). Expected score >= 0.28 for high alignment.
- **Diversity Metric:** Evaluated across `age_band`, `presentation`, and normalised Fitzpatrick categories. Target >= 60% coverage across the 6 baseline avatars.
- **Identity Metric (Exceptional):** Face embedding cosine similarity via InsightFace `buffalo_l` (ArcFace backbone) across different poses and backgrounds holding seed/identity constant.
