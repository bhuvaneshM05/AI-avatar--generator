# avatarpipe — Open-Source AI Human-Avatar Generation (PS02)

A fully modular pipeline for generating fictional AI avatars using open-weight
diffusion models. Built for the IncuBrix PS02 assessment.

---

## Architecture

```
[User] -> avatarpipe CLI (CPU)
              |
    +---------+------------------+
    |                            |
  new-job                    ingest
    |                            |
  AvatarSpec (Pydantic)    output_validator.py
  safety.py (pre-check)    manifest.py
  job_builder.py                 |
    |                    avatar_manifest.json
  jobs/<id>.json
    |
  prepare-notebook
    |
  [Kaggle T4 GPU Notebook]
  inference_kaggle.ipynb
  SDXL-base-1.0 (pinned)
    |
  result_fragment.json
  generated images
```

**CPU/GPU split**: ALL logic (validation, safety checks, job bundling,
output validation, manifest writing, evaluation, tests) runs on a plain
CPU-only laptop. ONLY the diffusion model inference step runs on the
Kaggle T4 GPU notebook.

---

## Quick Start

### 1. Install
```bash
pip install -e .
# or with conda:
conda env create -f environment.yml
conda activate avatarpipe
```

### 2. Create a spec file
```yaml
# my_avatar.yaml
age_band: adult
presentation: feminine
skin_tone: "Fitzpatrick III"
hair:
  style: "shoulder-length wavy"
  color: "dark brown"
attire: "business casual blazer, white shirt"
background: "modern office, soft bokeh"
pose: "neutral front-facing"
aspect_ratio: "1:1"
```

### 3. Build a job bundle
```bash
avatarpipe new-job --spec my_avatar.yaml
# Output: jobs/<uuid>.json
```

### 4. Run inference on Kaggle
```bash
avatarpipe prepare-notebook --job jobs/<uuid>.json
# Follow the printed Kaggle upload instructions
# Run notebooks/inference_kaggle.ipynb on Kaggle T4
# Download the output directory
```

### 5. Ingest results
```bash
avatarpipe ingest --job jobs/<uuid>.json --result-dir downloaded_output/
# Validates images + writes avatar_manifest.json
```

### 6. Evaluate
```bash
avatarpipe evaluate --run downloaded_output/avatar_manifest.json
```

### 7. Run tests (CPU only, < 5 seconds)
```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
src/avatarpipe/
  spec.py              - AvatarSpec schema (Pydantic v2)
  job_builder.py       - spec -> job bundle (JSON)
  safety.py            - pre-generation content policy checks
  inference_adapter.py - LocalCPUStubAdapter + NotebookAdapter
  output_validator.py  - post-generation image validation
  manifest.py          - avatar_manifest.json writer/reader
  evaluation/
    adherence.py       - CLIP-based prompt adherence scoring
    diversity.py       - attribute coverage metrics
    identity.py        - face embedding identity consistency (Exceptional)
  consent.py           - consent record management (Exceptional)
  cli.py               - avatarpipe CLI entry point
config/
  model_registry.yaml  - pinned model revisions (single source of truth)
  default_job_config.yaml
notebooks/
  inference_kaggle.ipynb - Kaggle GPU inference notebook (NOT Colab)
tests/
  unit/                - fast, CPU-only, no GPU/network
  integration/         - CLI chain tests with LocalCPUStubAdapter
  e2e/                 - recorded/replayed full pipeline tests
benchmarks/
  run_benchmark.py     - produces benchmarks/report.json
evidence/
  test_matrix/         - all required test cases with saved outputs
  attempts/            - every generated attempt (incl. rejected)
  evidence_index.md    - rubric -> file mapping
```

---

## Constraints (enforced by design)

- **No paid APIs**: only open-weight models from HuggingFace Hub
- **No Colab**: Kaggle only (no managed-runtime policy issues)
- **No ethnicity/nationality field**: intentionally omitted from AvatarSpec
- **Consent required**: `reference_images` without `consent_id` raises ValidationError
- **Deterministic**: every run is reproducible from seed + pinned model revision
- **All tests on CPU**: `python -m pytest tests/` needs no GPU

See `SOURCES.md` for all model/library licenses and `AI_USE.md` for AI assistance disclosure.
