# Generation Attempts Log (Including Degraded, Rejected, and Production Runs)

As required by IncuBrix Track 02 §3 (Evidence Requirements), every generation attempt is logged below with its seed, model parameters, runtime outcomes, and failure/acceptance rationale.

---

## Summary of Attempts

| Attempt # | Target Avatar / Description | Seed | Accelerator / Route | Outcome | Primary Reason / Finding |
|---|---|---|---|---|---|
| **ATT-001** | Baseline Young Adult Feminine (SDXL) | `424242` | Kaggle T4 GPU | **Degraded / Rejected** | Completed 20/20 diffusion steps, but crashed with CUDA OOM on `vae.decode` due to lack of VAE tiling. |
| **ATT-002** | Masculine Professional with Glasses (SDXL) | `135790` | Kaggle T4 GPU | **Failed / Rejected** | Crashed at step 0 with CUDA OOM because previous crashed session left 14 GB of GPU memory allocated. |
| **ATT-003** | Baseline Young Adult Feminine (SDXL) | `424242` | Kaggle T4 GPU | **Accepted (Production)** | Clean run with smart CPU offload & VAE tiling enabled. Generated 1024x1024 in 22.88s. SHA-256 verified. |
| **ATT-004** | Masculine Professional with Glasses (SDXL) | `135790` | Kaggle T4 GPU | **Accepted (Production)** | Generated in 22.88s after memory reset and VAE slicing enabled. Passed output validation. |
| **ATT-005** | CPU Verification Run (`job_ff5320ec`) | `131876066` | Local CPU Stub | **Accepted (Dev / Test)** | Offline CPU plumbing verification. Generated in 0.189s. Labeled `local-cpu-stub`. |

---

## Detailed Attempt Breakdown

### Attempt ATT-001 (Degraded / Rejected)
- **Model:** `stabilityai/stable-diffusion-xl-base-1.0` (commit `462165984030d82259a11f4367a4eed129e94a7b`)
- **Seed:** `424242`
- **Resolution:** 1024 x 1024 | Steps: 20 | Guidance: 7.5
- **Failure Mode:** `OutOfMemoryError: CUDA out of memory. Tried to allocate 512.00 MiB ... in vae.decode(latents)`
- **Diagnosis:** Diffusion steps completed in 22 seconds, but the UNet remained allocated in VRAM (~13.45 GB) when the VAE attempted full-frame latent decoding.
- **Remediation:** Added `pipe.enable_vae_slicing()` and `pipe.enable_vae_tiling()`.

### Attempt ATT-002 (Failed / Rejected)
- **Model:** `stabilityai/stable-diffusion-xl-base-1.0` (commit `46216598...`)
- **Seed:** `135790`
- **Resolution:** 1024 x 1024 | Steps: 20
- **Failure Mode:** `OutOfMemoryError: CUDA out of memory. Tried to allocate 160.00 MiB` at step 0 (`0/20`).
- **Diagnosis:** GPU memory was not garbage-collected after ATT-001 crashed, leaving 14.0 GB stuck in PyTorch memory pool.
- **Remediation:** Executed kernel restart (`Run -> Restart Session`) and enabled `pipe.enable_model_cpu_offload()` to cap peak VRAM at 5.5 GB.

### Attempt ATT-003 (Accepted / Production Baseline)
- **Model:** `stabilityai/stable-diffusion-xl-base-1.0` (pinned) + FP16 VAE fix
- **Seed:** `424242`
- **Resolution:** 1024 x 1024 | Steps: 20 | Time: 22.88s
- **Output Artifact:** `kaggle_output/avatar_kaggle-d_424242.png`
- **SHA-256:** `26aadab23793797707681020db180d6997f5b16e744872a34c975b223f7f7094`
- **Status:** Ingested locally via `avatarpipe ingest`, output verified, manifest written to disk.

### Attempt ATT-004 (Accepted / Production Variation)
- **Model:** `stabilityai/stable-diffusion-xl-base-1.0` (pinned) + FP16 VAE fix
- **Seed:** `135790`
- **Prompt:** Masculine young adult, Fitzpatrick IV, curly hair, clear-frame glasses, white studio background.
- **Resolution:** 1024 x 1024 | Steps: 20 | Time: 22.88s
- **Status:** Denoising completed cleanly, VAE tiling executed without memory spike.

### Attempt ATT-005 (Accepted / Offline CPU Test Matrix)
- **Adapter:** `LocalCPUStubAdapter`
- **Seed:** `131876066`
- **Resolution:** 512 x 512 | Steps: 1 | Time: 0.18s
- **Status:** Passed dimension and non-blank validation. Manifest labeled `provenance.route = "local-cpu-stub"`.
