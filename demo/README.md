# Unedited 8-Minute Candidate Demo Guide & Video Script

This document provides the exact rehearsal structure, commands, and narrative script for recording the unedited 8-minute submission video required by the IncuBrix Track 02 evaluation guidelines (Page 4).

---

## Demo Timing Budget (Total <= 8:00)

| Timestamp | Section | Key Action / Command | Deliverable Demonstrated |
|---|---|---|---|
| **0:00 - 1:15** | Setup & Clean Tests | `git status`, `python -m pytest tests/` | Clean repo, 98 tests passing on CPU in 3s |
| **1:15 - 2:30** | Spec Creation & Job Builder | `python -m avatarpipe.cli new-job --spec example_spec.yaml` | Pydantic validation, deterministic seed, safety screening |
| **2:30 - 4:00** | Offline CPU Run & Manifest | `python -m avatarpipe.cli run-local --job jobs/<id>.json` | CPU plumbing, output validator, manifest generation |
| **4:00 - 5:30** | Accelerator (Kaggle GPU) | Walk through `notebooks/inference_kaggle.ipynb` | SDXL Base 1.0 pinned run, 20 steps, 22.88s execution |
| **5:30 - 6:30** | Ingest & Verification | `python -m avatarpipe.cli ingest ...`, `avatarpipe evaluate ...` | Output validation, SHA-256 hash match, evaluation table |
| **6:30 - 7:15** | Failure & Recovery | Run corrupted image test / consent refusal | Deliberate failure detection & error recovery |
| **7:15 - 8:00** | Code-Level Decision | Explain `spec.py` / `safety.py` / `inference_adapter.py` | Architectural ownership & defense of trade-offs |

---

## Step-by-Step Recording Script

### 1. Introduction & Automated Testing (0:00 - 1:15)
- **Speak:** "Hello, I am presenting my solution for IncuBrix Track 02 — Open-Source AI Human-Avatar Generation. I will demonstrate the complete system running under our CPU and free-accelerator constraints."
- **Terminal:**
  ```powershell
  git status
  python -m pytest tests/ -q --tb=no
  ```
- **Explain:** "Notice all 98 unit, integration, and end-to-end tests run 100% on this local CPU laptop in approximately 3 seconds. Google Colab and paid commercial APIs are completely excluded."

### 2. Spec Validation & Job Building (1:15 - 2:30)
- **Open:** `example_spec.yaml` in VS Code/editor.
- **Explain:** "Our schema decouples appearance traits into independent attributes: age band, skin tone via the Fitzpatrick dermatological scale, attire, and background. There is no nationality or ethnicity field in the data contract, preventing stereotyping."
- **Terminal:**
  ```powershell
  python -m avatarpipe.cli new-job --spec example_spec.yaml
  ```
- **Explain:** "The CLI validates the schema, checks the prompt with our rule-based safety engine, assigns a cryptographically random 32-bit seed via `secrets.randbits(32)`, and serializes a portable job bundle."

### 3. Local CPU Run & Output Validation (2:30 - 4:00)
- **Terminal:**
  ```powershell
  python -m avatarpipe.cli run-local --job jobs/<job_id>.json --output-dir local_output/
  ```
- **Explain:** "For offline testing without a GPU, our `LocalCPUStubAdapter` executes the entire pipeline in 0.2 seconds. The output validator checks readability, dimensions, and pixel variance, producing an official `avatar_manifest.json` labeled `local-cpu-stub`."

### 4. Free Accelerator Inference (4:00 - 5:30)
- **Switch to Browser:** Show Kaggle notebook `inference_kaggle.ipynb`.
- **Explain:** "For the actual high-resolution diffusion inference, we run on Kaggle's free Tesla T4 GPU. We pin `stabilityai/stable-diffusion-xl-base-1.0` and the FP16 VAE fix. Using `pipe.enable_model_cpu_offload()` and `pipe.enable_vae_tiling()`, peak VRAM is capped at ~5.5 GB. Inference finishes 20 steps in 22.88 seconds."

### 5. Local Ingest & Metrics (5:30 - 6:30)
- **Terminal:**
  ```powershell
  python -m avatarpipe.cli ingest --job jobs/<job_id>.json --result-dir kaggle_output/
  python -m avatarpipe.cli evaluate --run kaggle_output/avatar_manifest.json
  ```
- **Explain:** "The local CLI verifies the downloaded image's SHA-256 hash against Kaggle's fragment, confirms 1024x1024 dimensions, writes the manifest, and evaluates diversity and adherence metrics."

### 6. Failure Injection & Recovery (6:30 - 7:15)
- **Terminal:**
  ```powershell
  python -m pytest tests/integration/test_matrix_edge_cases.py -v
  ```
- **Explain:** "Here we demonstrate deliberate failure handling:
  1. An ambiguous specification triggers warning flags without crashing.
  2. An unsafe request is caught by the safety engine and logged with a structured refusal.
  3. A corrupted file is caught by the output validator.
  4. An unconsented reference image is refused immediately at schema validation time."

### 7. Code-Level Decision (7:15 - 8:00)
- **Open:** `src/avatarpipe/inference_adapter.py`.
- **Explain:** "One crucial code decision was our `InferenceAdapter` abstract base class. It separates the local CPU plumbing from remote accelerator I/O at the type level. This allowed us to build 98 automated tests without needing a GPU, while making the pipeline portable to any future accelerator like Lightning.ai or HF ZeroGPU."

---

## Video File Submission
- Upload your unedited video (`.mp4`, `< 8 minutes`) to Google Drive, YouTube (unlisted), or your preferred hosting.
- Paste the shareable URL into `demo/video_link.txt` and in Sheet `00_START` of the official workbook.
