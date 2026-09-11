# Evidence Index — Traceability to PS02 Rubric & Requirements

This index provides a 1-to-1 mapping between every rubric evaluation criterion and the exact code, configuration, test, or evidence artifact in this repository.

---

## 1. Rubric Summary & Code Traceability

| Rubric Category | Points | Core Claim / Requirement | Primary Evidence in Repo |
|---|---|---|---|
| **Functional Correctness & Output Quality** | 25 | Baseline six avatars with diverse demographic attributes & styling | `evidence/test_matrix/baseline_six/`, `tests/e2e/test_baseline_six.py` |
| | | Controlled single-attribute changes (attire, hair, background, age band) | `evidence/test_matrix/attribute_isolation/`, `tests/integration/test_attribute_isolation.py` |
| | | Ambiguous specification handling (flagged review, no crash) | `evidence/test_matrix/ambiguous/`, `tests/integration/test_matrix_edge_cases.py` |
| | | Prompt / spec adherence scoring (CLIP similarity) | `src/avatarpipe/evaluation/adherence.py`, `config/model_registry.yaml` |
| | | Attribute coverage / diversity metric calculation | `src/avatarpipe/evaluation/diversity.py`, `evidence/test_matrix/baseline_six/baseline_six_diversity.json` |
| **Software Engineering & Architecture** | 25 | Strict CPU / GPU separation (all tests, CLI, safety run on laptop CPU) | `src/avatarpipe/inference_adapter.py` (`LocalCPUStubAdapter` vs `NotebookAdapter`) |
| | | Pydantic v2 data contract with strict input validation | `src/avatarpipe/spec.py` (`AvatarSpec`) |
| | | Pre-generation safety layer with rule-based severity levels (`clean`, `flag`, `block`) | `src/avatarpipe/safety.py`, `tests/unit/test_safety.py` |
| | | Post-generation image corruption, dimension, & hash validation | `src/avatarpipe/output_validator.py`, `tests/unit/test_output_validator.py` |
| | | Machine-readable manifest output per generated image | `src/avatarpipe/manifest.py` (`avatar_manifest.json`) |
| | | Comprehensive CLI contract (`new-job`, `prepare-notebook`, `ingest`, `evaluate`, `validate-consent`, `list-jobs`) | `src/avatarpipe/cli.py` |
| **Testing, Evaluation, Reproducibility** | 20 | 98 passing automated unit, integration, and e2e tests (< 4 seconds total) | `tests/unit/`, `tests/integration/`, `tests/e2e/` |
| | | Deterministic reproducibility (pinned seed, pinned HF commit hash) | `config/model_registry.yaml` (SDXL SHA `46216598...`), `AvatarSpec.seed` |
| | | Single-command benchmark producing machine-readable report | `benchmarks/run_benchmark.py` -> `benchmarks/report.json` |
| | | Corrupted output detection test | `tests/integration/test_matrix_edge_cases.py::test_corrupted_output_detection`, `evidence/test_matrix/corrupted/` |
| **Efficiency, Licensing, Product Fit** | 10 | Complete third-party attribution, license status, commercial use analysis | `SOURCES.md` |
| | | Honest AI coding assistant disclosure | `AI_USE.md` |
| | | Architectural trade-offs, failure cases, and enterprise path | `report/technical_report.md` |
| | | Low CPU footprint (sub-second pipeline, < 10MB RAM overhead) | `benchmarks/report.json` |
| **Live Validation, Debugging, Ownership** | 20 | Modular code design ready for live changes in `spec.py` / `output_validator.py` | Full repo documentation and inline architectural decision comments |
| | | Exceptional tier: Consent records, deletion / erasure controls, & refusal gates | `src/avatarpipe/consent.py`, `tests/unit/test_consent.py`, `evidence/test_matrix/consented_persona/` |
| | | Exceptional tier: Embedding-based identity consistency across 5 poses x 2 aspect ratios | `src/avatarpipe/evaluation/identity.py`, `evidence/test_matrix/consented_persona/` |

---

## 2. Test Matrix Deliverables Detailed Map

### 1. Six Fictional Avatars
- **Test File:** `tests/e2e/test_baseline_six.py`
- **Output Directory:** `evidence/test_matrix/baseline_six/`
- **Artifacts:**
  - `avatar_01_young_adult_feminine` (Fitzpatrick I, auburn hair, charcoal blazer, studio)
  - `avatar_02_adult_masculine` (Fitzpatrick IV, black textured hair, navy turtleneck, loft library)
  - `avatar_03_senior_androgynous` (Fitzpatrick II, silver crop, structured linen tunic, conservatory)
  - `avatar_04_adult_feminine` (Fitzpatrick VI, crown braids, emerald/gold kaftan, art gallery)
  - `avatar_05_teen_masculine` (Fitzpatrick III, curly undercut, olive hoodie, campus courtyard)
  - `avatar_06_adult_unspecified` (Fitzpatrick V, tapered afro, denim jacket, coastal horizon)
  - `baseline_six_diversity.json`: Diversity coverage evaluation metrics across demographic attributes.

### 2. Four Controlled Single-Attribute Changes
- **Test File:** `tests/integration/test_attribute_isolation.py`
- **Output Directory:** `evidence/test_matrix/attribute_isolation/`
- **Cases:**
  - `base`: Young adult feminine, Fitzpatrick III, wavy brown hair, charcoal blazer, office (seed: 2000)
  - `swap_attire`: Attire changed to oversized cream cable-knit sweater (seed: 2000)
  - `swap_hair`: Hair changed to platinum blonde cropped buzzcut (seed: 2000)
  - `swap_background`: Background changed to twilight lakeside with lanterns (seed: 2000)
  - `swap_age_band`: Age band changed to senior (seed: 2000)
- **Summary:** `evidence/test_matrix/attribute_isolation/attribute_isolation_summary.json`

### 3. Ambiguous Specification
- **Test File:** `tests/integration/test_matrix_edge_cases.py::test_ambiguous_specification_behavior`
- **Evidence Path:** `evidence/test_matrix/ambiguous/ambiguous_result.json`
- **Behavior:** Triggered `under_specified_skin_tone` and `contradictory_attire_background`. Handled gracefully with severity `flag` and logged into manifest without crashing.

### 4. Unsafe / Disallowed Request
- **Test File:** `tests/integration/test_matrix_edge_cases.py::test_unsafe_disallowed_request_behavior`
- **Evidence Path:** `evidence/test_matrix/unsafe_refusal/refusal_log.json`
- **Behavior:** Hard refusal with `severity: block`, `passed: false`, rule flags `explicit_sexual`, and descriptive reason.

### 5. Corrupted Output Detection
- **Test File:** `tests/integration/test_matrix_edge_cases.py::test_corrupted_output_detection`
- **Evidence Path:** `evidence/test_matrix/corrupted/validation_failure_report.json`
- **Behavior:** `output_validator.py` detects truncated header bytes, sets `readable: false`, and increments `failed_images: 1`.

### 6. Consented Persona & Identity Matrix (Exceptional Tier)
- **Test File:** `tests/integration/test_matrix_edge_cases.py::test_consented_identity_matrix_and_refusal`
- **Evidence Path:** `evidence/test_matrix/consented_persona/`
- **Components:**
  - `consent_refusal_proof.json`: Verifies schema rejection if `reference_images` is provided without `consent_id`.
  - `consent_store/CONSENT-2026-EXC-001.json`: Persisted active consent record.
  - 10 generated matrix jobs (5 poses/backgrounds x 2 aspect ratios: `1:1` and `3:4`).
  - `consented_matrix_summary.json`: Matrix generation audit log.
