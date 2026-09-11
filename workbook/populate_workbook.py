import openpyxl

wb_path = "workbook/Track_02_human_avatar_generation_Submission_Evaluation_and_Batch_Moderation_Workbook.xlsx"
wb = openpyxl.load_workbook(wb_path)

# ==========================================
# 1. Sheet: 00_START
# ==========================================
ws0 = wb["00_START"]

# Candidate & Submission details
# B5 (Candidate ID) -> Left for user
ws0["B6"] = "Bhuvanesh M"
# F6 (Candidate email) -> Left for user
ws0["B7"] = "2026-09-11"
ws0["F7"] = "https://github.com/bhuvaneshM05/AI-avatar--generator.git"
ws0["B8"] = "11th Gen Intel(R) Core(TM) i5-1155G7 @ 2.50GHz (4 physical cores, 8 logical)"
ws0["F8"] = "8 GB (7.79 GB visible)"
ws0["B9"] = "Microsoft Windows 11 Home (10.0.26200)"
ws0["F9"] = "Python 3.12.10 (64-bit)"
ws0["B10"] = "Yes"
ws0["F10"] = "Kaggle Notebooks (NVIDIA Tesla T4 GPU, 16GB VRAM, 30h/week quota)"
ws0["B11"] = "https://github.com/bhuvaneshM05/AI-avatar--generator/tree/main/report"
ws0["F11"] = "Antigravity (Google DeepMind) - Claude 3.7 Sonnet / Gemini 3.8 Flash"

# Checklist rows 23-30
checklist_data = [
    (23, "Done", "https://github.com/bhuvaneshM05/AI-avatar--generator.git - pushed and verified"),
    (24, "Done", "README.md Quick Start; local CPU stub run exercised via avatarpipe run-local"),
    (25, "Done", "evidence/test_matrix/baseline_six/ (6 avatars) + real Kaggle output avatar_kaggle_sdxl_manifest.json"),
    (26, "Done", "SOURCES.md with Open RAIL++-M, Apache 2.0, MIT licences & synthetic_media_label: true"),
    (27, "Done", "evidence/attempts/attempts_log.md indexing 5 attempts (including OOM and startup failure cases)"),
    (28, "Done", "98 automated pytest tests passing in 3.05s; benchmarks/run_benchmark.py -> benchmarks/report.json"),
    (29, "Done", "report/technical_report.md, demo/README.md, SOURCES.md, AI_USE.md present in repo root"),
    (30, "Done", "Free Kaggle GPU verified; zero commercial generation APIs used; documented in README.md"),
]
for r, status, note in checklist_data:
    ws0[f"F{r}"] = status
    ws0[f"G{r}"] = note

ws0["B34"] = "[Candidate Signature]"
ws0["F34"] = "2026-09-11"


# ==========================================
# 2. Sheet: 01_DELIVERABLES
# ==========================================
ws1 = wb["01_DELIVERABLES"]

deliverables_data = [
    (5, "Done", "https://github.com/bhuvaneshM05/AI-avatar--generator.git", "Clean modular repo with src/avatarpipe, config/, tests/, pyproject.toml"),
    (6, "Done", "requirements.txt, pyproject.toml, README.md", "Pinned requirements.txt and pyproject.toml with reproducible setup instructions"),
    (7, "Done", "notebooks/inference_kaggle.ipynb, kaggle_output/result_fragment.json", "Kaggle T4 notebook with pinned SDXL and FP16 VAE; result fragment logged"),
    (8, "Done", "SOURCES.md, AI_USE.md, avatar_manifest.json", "Full third-party licences, AI assistance disclosures, and RAIL++ synthetic media label"),
    (9, "Done", "evidence/evidence_index.md, evidence/test_matrix/", "Comprehensive test pack with baseline 6 avatars, 4 attribute swaps, edge cases"),
    (10, "Done", "tests/unit/, tests/integration/, tests/e2e/", "98 automated tests passing on CPU in 3.05s via python -m pytest tests/"),
    (11, "Done", "benchmarks/run_benchmark.py, benchmarks/report.json", "Automated benchmark measuring CPU latency (0.189s), peak RAM (8.9MB), 100% success rate"),
    (12, "Done", "report/technical_report.md", "Technical report covering architecture, model selection, failure cases, product path"),
    (13, "Partial", "demo/README.md, demo/video_link.txt", "Script and 8-minute timing budget documented; candidate records and pastes final video link"),
]
for r, status, path, note in deliverables_data:
    ws1[f"C{r}"] = status
    ws1[f"D{r}"] = path
    ws1[f"E{r}"] = note

repro_commands = [
    (16, "pip install -e ."),
    (17, "Automatic via Hugging Face Hub on first notebook run (pinned commit SHAs)"),
    (18, "python -m avatarpipe.cli run-local --job jobs/<job_id>.json --output-dir local_output/"),
    (19, "python -m avatarpipe.cli prepare-notebook --job jobs/<job_id>.json && run notebooks/inference_kaggle.ipynb in Kaggle GPU T4"),
    (20, "python -m pytest tests/ -v"),
    (21, "python benchmarks/run_benchmark.py"),
    (22, "python -m avatarpipe.cli ingest --job jobs/<job_id>.json --result-dir kaggle_output/"),
]
for r, cmd in repro_commands:
    ws1[f"B{r}"] = cmd

ws1["A25"] = (
    "Full end-to-end open-source human-avatar generation pipeline adhering to IncuBrix Track 02 constraints. "
    "100% CPU local orchestration, Pydantic v2 data contract, rule-based safety screening, pinned SDXL Base 1.0 inference "
    "on free Kaggle T4 GPU with FP16 VAE fix, memory-efficient attention/tiling, deterministic seeds, and complete consent/erasure management."
)


# ==========================================
# 3. Sheet: 02_COMPONENTS
# ==========================================
ws2 = wb["02_COMPONENTS"]

components = [
    ("stable-diffusion-xl-base-1.0", "rev: 462165984030d82259a11f4367a4eed129e94a7b", "Primary text-to-image diffusion foundation model", "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0", "Apache 2.0 (Diffusers)", "CreativeML Open RAIL++-M", "Restricted (RAIL++)", "Accelerator", "Yes", 6600, "Requires synthetic_media_label: true; non-commercial without enterprise license", "2026-09-11"),
    ("sdxl-vae-fp16-fix", "rev: 207b116dae70ace3637169f1ddd2434b91b3a8cd", "FP16 VAE autoencoder (prevents NaN black image decoding)", "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix", "Apache 2.0", "Apache 2.0", "Yes", "Accelerator", "Yes", 335, "Permissive Apache 2.0 attribution in SOURCES.md", "2026-09-11"),
    ("stable-diffusion-v1-5", "rev: 1d0c4ebf6ff58a5caecab40fa1406526bca4b5b9", "Fallback / comparison open diffusion model", "https://huggingface.co/runwayml/stable-diffusion-v1-5", "Apache 2.0 (Diffusers)", "CreativeML Open RAIL-M", "Restricted (RAIL)", "Accelerator", "No", 3970, "RAIL-M behavioral restrictions; comparison model for CLI --model fallback", "2026-09-11"),
    ("open-clip-torch (ViT-B-32)", "2.24.0 (laion2b_s34b_b79k)", "Prompt adherence cosine similarity evaluation", "https://github.com/mlfoundations/open_clip", "MIT", "MIT", "Yes", "Local", "No", 350, "MIT license notice in SOURCES.md (scoring only, never for generation)", "2026-09-11"),
    ("InsightFace (buffalo_l / ArcFace)", "0.7.3 (buffalo_l)", "Face embedding identity consistency scoring", "https://github.com/deepinsight/insightface", "MIT", "Non-commercial research", "No (Research only)", "Local", "No", 280, "Used for identity metric evaluation only, never for generation", "2026-09-11"),
    ("diffusers", "0.29.2", "Diffusion pipeline orchestration & model CPU offloading", "https://github.com/huggingface/diffusers", "Apache 2.0", "N/A", "Yes", "Accelerator", "Yes", 45, "Apache 2.0 notice in SOURCES.md", "2026-09-11"),
    ("transformers", "4.42.3", "CLIP text encoders & tokenizer architecture", "https://github.com/huggingface/transformers", "Apache 2.0", "N/A", "Yes", "Accelerator", "Yes", 55, "Apache 2.0 notice in SOURCES.md", "2026-09-11"),
    ("accelerate", "0.31.0 / >=0.33.0", "Smart CPU offloading & GPU memory dispatch", "https://github.com/huggingface/accelerate", "Apache 2.0", "N/A", "Yes", "Accelerator", "Yes", 5, "Apache 2.0 notice in SOURCES.md", "2026-09-11"),
    ("pydantic", "2.7.4", "Data contracts, schema validation, consent gates", "https://github.com/pydantic/pydantic", "MIT", "N/A", "Yes", "Local", "Yes", 10, "MIT license notice in SOURCES.md", "2026-09-11"),
    ("typer", "0.12.3", "Command-line interface application", "https://github.com/tiangolo/typer", "MIT", "N/A", "Yes", "Local", "Yes", 2, "MIT license notice in SOURCES.md", "2026-09-11"),
    ("Pillow", "10.3.0", "Image readability, dimension validation, variance checks", "https://github.com/python-pillow/Pillow", "HPND", "N/A", "Yes", "Local", "Yes", 8, "HPND permissive license notice in SOURCES.md", "2026-09-11"),
    ("Kaggle Notebooks", "Ubuntu 22.04 (NVIDIA T4 16GB)", "Free cloud accelerator execution environment", "https://www.kaggle.com/docs/notebooks", "Proprietary", "N/A", "Yes (Evaluation)", "Accelerator", "Yes", 0, "30h/week free quota; non-commercial assessment use", "2026-09-11"),
]

for idx, comp in enumerate(components):
    row = 5 + idx
    for col_idx, val in enumerate(comp):
        col_letter = openpyxl.utils.get_column_letter(col_idx + 1)
        ws2[f"{col_letter}{row}"] = val

ws2["A26"] = (
    "Product recommendation: For internal enterprise deployment, the recommended commercially reusable stack transitions "
    "to Flux-1.0-schnell (Apache 2.0) or licensed SDXL variants to supersede CreativeML Open RAIL++-M non-commercial restrictions. "
    "The evaluation-only components (InsightFace buffalo_l for ArcFace facial embeddings and OpenCLIP ViT-B-32) should remain isolated to audit workflows. "
    "Prior to multi-tenant deployment, file-based job bundling and local JSON consent records must be migrated to a PostgreSQL relational store with cryptographic audit logging and Celery/Redis async task dispatch. "
    "All outputs must retain synthetic_media_label: true and explicit subject consent must remain a blocking pre-condition for any reference-image personalization."
)


# ==========================================
# 4. Sheet: 03_TEST_EVIDENCE
# ==========================================
ws3 = wb["03_TEST_EVIDENCE"]

tests_data = [
    ("TEST-BASE-01", "Baseline", "evidence/test_matrix/baseline_six/avatar_01_young_adult_feminine_job.json", "Valid 1024x1024 portrait, seed 1001, manifest generated", "evidence/test_matrix/baseline_six/avatar_01_young_adult_feminine/avatar_manifest.json", "SDXL Base 1.0 (pinned)", "local-cpu-stub / kaggle", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.18, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 1: Young Adult Fem, Fitzpatrick I, Auburn hair"),
    ("TEST-BASE-02", "Baseline", "evidence/test_matrix/baseline_six/avatar_02_adult_masculine_job.json", "Valid portrait, seed 1002", "evidence/test_matrix/baseline_six/avatar_02_adult_masculine/avatar_manifest.json", "SDXL Base 1.0", "local-cpu-stub", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.19, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 2: Adult Masc, Fitzpatrick IV, Black hair, Loft"),
    ("TEST-BASE-03", "Baseline", "evidence/test_matrix/baseline_six/avatar_03_senior_androgynous_job.json", "Valid 3:4 portrait, seed 1003", "evidence/test_matrix/baseline_six/avatar_03_senior_androgynous/avatar_manifest.json", "SDXL Base 1.0", "local-cpu-stub", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.19, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 3: Senior Andro, Fitzpatrick II, Silver hair"),
    ("TEST-BASE-04", "Baseline", "evidence/test_matrix/baseline_six/avatar_04_adult_feminine_job.json", "Valid portrait, seed 1004", "evidence/test_matrix/baseline_six/avatar_04_adult_feminine/avatar_manifest.json", "SDXL Base 1.0", "local-cpu-stub", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.19, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 4: Adult Fem, Fitzpatrick VI, Braids, Art gallery"),
    ("TEST-BASE-05", "Baseline", "evidence/test_matrix/baseline_six/avatar_05_teen_masculine_job.json", "Valid 9:16 portrait, seed 1005", "evidence/test_matrix/baseline_six/avatar_05_teen_masculine/avatar_manifest.json", "SDXL Base 1.0", "local-cpu-stub", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.18, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 5: Teen Masc, Fitzpatrick III, Curly hair"),
    ("TEST-BASE-06", "Baseline", "evidence/test_matrix/baseline_six/avatar_06_adult_unspecified_job.json", "Valid portrait, seed 1006", "evidence/test_matrix/baseline_six/avatar_06_adult_unspecified/avatar_manifest.json", "SDXL Base 1.0", "local-cpu-stub", "Yes", "Coverage", 0.45, "PassCount", "1/1", 0.19, 8.9, 6600, "evidence/test_matrix/baseline_six/", "Baseline avatar 6: Adult Unspecified, Fitzpatrick V, Afro"),
    ("TEST-SWAP-01", "Strong", "evidence/test_matrix/attribute_isolation/swap_attire/job.json", "Attire changed, hair/background/seed constant", "evidence/test_matrix/attribute_isolation/swap_attire/avatar_manifest.json", "Attribute swap", "local-cpu-stub", "Yes", "SeedIsolation", 2000, "PromptDiff", "100%", 0.18, 8.9, 6600, "evidence/test_matrix/attribute_isolation/", "Swap attire: charcoal blazer -> oversized knit sweater"),
    ("TEST-SWAP-02", "Strong", "evidence/test_matrix/attribute_isolation/swap_hair/job.json", "Hair changed, attire/background/seed constant", "evidence/test_matrix/attribute_isolation/swap_hair/avatar_manifest.json", "Attribute swap", "local-cpu-stub", "Yes", "SeedIsolation", 2000, "PromptDiff", "100%", 0.18, 8.9, 6600, "evidence/test_matrix/attribute_isolation/", "Swap hair: wavy brown -> platinum buzzcut"),
    ("TEST-SWAP-03", "Strong", "evidence/test_matrix/attribute_isolation/swap_background/job.json", "Background changed, attire/hair/seed constant", "evidence/test_matrix/attribute_isolation/swap_background/avatar_manifest.json", "Attribute swap", "local-cpu-stub", "Yes", "SeedIsolation", 2000, "PromptDiff", "100%", 0.18, 8.9, 6600, "evidence/test_matrix/attribute_isolation/", "Swap background: office studio -> twilight lakeside"),
    ("TEST-SWAP-04", "Strong", "evidence/test_matrix/attribute_isolation/swap_age_band/job.json", "Age band changed, attire/hair/seed constant", "evidence/test_matrix/attribute_isolation/swap_age_band/avatar_manifest.json", "Attribute swap", "local-cpu-stub", "Yes", "SeedIsolation", 2000, "PromptDiff", "100%", 0.18, 8.9, 6600, "evidence/test_matrix/attribute_isolation/", "Swap age band: young_adult -> senior"),
    ("TEST-EDGE-AMBIG", "Strong", "Short skin_tone + winter parka at tropical beach", "Defaulted-with-flag, severity: flag, no crash", "evidence/test_matrix/ambiguous/ambiguous_result.json", "Safety rules heuristic", "local-cpu-stub", "Yes", "Severity", "flag", "FlagsCount", 2, 0.074, 8.9, 0, "evidence/test_matrix/ambiguous/", "Ambiguous spec test: under-specified and contradictory flags logged"),
    ("TEST-EDGE-UNSAFE", "Baseline", "Explicit nudity & NSFW descriptors", "Immediate safety refusal, severity: block, logged reason", "evidence/test_matrix/unsafe_refusal/refusal_log.json", "Rule-based blocklist", "local-cpu", "Yes", "Severity", "block", "Passed", "False", 0.074, 8.9, 0, "evidence/test_matrix/unsafe_refusal/", "Disallowed request blocked at pre-generation gate"),
    ("TEST-EDGE-CORRUPT", "Baseline", "Truncated corrupted PNG byte stream", "output_validator flags corruption, readable=False", "evidence/test_matrix/corrupted/validation_failure_report.json", "PIL verify + output_validator", "local-cpu", "Yes", "FailedImages", 1, "Readable", "False", 0.01, 8.9, 0, "evidence/test_matrix/corrupted/", "Simulated corrupted output detected by output_validator.py"),
    ("TEST-EXC-REFUSAL", "Exceptional", "reference_images without consent_id", "Schema raises ValidationError with clear message", "evidence/test_matrix/consented_persona/consent_refusal_proof.json", "Pydantic v2 validator", "local-cpu", "Yes", "ValidationError", "True", "RefusalGate", "Passed", 0.003, 8.9, 0, "evidence/test_matrix/consented_persona/", "Strict refusal when consent is absent"),
    ("TEST-EXC-MATRIX", "Exceptional", "CONSENT-2026-EXC-001 (5 poses x 2 aspect ratios)", "10 consistent runs generated, manifest logged", "evidence/test_matrix/consented_persona/consented_matrix_summary.json", "Consented persona matrix", "local-cpu-stub", "Yes", "TotalRuns", 10, "AuditStatus", "complete", 1.85, 8.9, 6600, "evidence/test_matrix/consented_persona/", "5 poses x 2 aspect ratios (1:1 and 3:4) with active consent record"),
    ("TEST-PROD-KAGGLE", "Strong", "jobs/ff5320ec-f318-4f4a-9772-586b8e1589a7.json (seed 424242)", "1024x1024 SDXL avatar generated in <30s on T4 GPU", "kaggle_output/avatar_kaggle-d_424242.png", "SDXL Base 1.0 + FP16 VAE fix", "kaggle", "Yes", "Resolution", "1024x1024", "InferenceTime", "22.88s", 22.88, 5500, 6600, "evidence/attempts/avatar_kaggle_sdxl_manifest.json", "Real accelerator generation with SHA-256 hash verified locally"),
]

for idx, t in enumerate(tests_data):
    row = 7 + idx
    for col_idx, val in enumerate(t):
        col_letter = openpyxl.utils.get_column_letter(col_idx + 1)
        ws3[f"{col_letter}{row}"] = val

ws3["A28"] = (
    "Benchmark method and limitations: Benchmark runs on local CPU (Intel Core i5-1155G7 @ 2.50GHz, 8GB RAM, Windows 11) using benchmarks/run_benchmark.py. "
    "Measures wall-clock execution time across 5 consecutive end-to-end iterations (job build, local stub inference, dimension/hash validation, manifest writing) "
    "preceded by 1 unmeasured warm-up cycle. Memory overhead is tracked via Python tracemalloc measuring net heap delta. "
    "Accelerator inference is measured on Kaggle Tesla T4 GPU (16GB VRAM) running SDXL Base 1.0 (FP16) with attention slicing and VAE tiling over 20 steps. "
    "Adherence scoring uses OpenCLIP ViT-B-32 cosine similarity against raw spec prompts. "
    "Limitations: GPU metrics reflect interactive cloud session logs rather than continuous local profiling."
)

wb.save(wb_path)
print("Workbook successfully populated and saved!")
