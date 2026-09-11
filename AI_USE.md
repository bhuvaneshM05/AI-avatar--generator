# AI_USE.md — AI Assistance Disclosure

This document discloses all use of AI coding assistants in building this project,
as required by the PS02 assessment constraints (§0, rule 7).

---

## AI Tool Used

**Antigravity** (Google DeepMind Advanced Agentic Coding assistant)
- Model: Claude Sonnet 4.6 (Thinking)
- Conversation ID: 608dd55e-ad28-4e88-8390-e5ea5699ed63

---

## What Was Asked

The AI agent was given the complete PS02 build specification document and asked to:

1. Explain the implementation plan
2. Make technology decisions (model choice, accelerator, target tier)
3. Scaffold the entire repository structure
4. Implement all Python source modules:
   - `src/avatarpipe/spec.py` (AvatarSpec schema)
   - `src/avatarpipe/job_builder.py` (job bundling)
   - `src/avatarpipe/safety.py` (content policy)
   - `src/avatarpipe/inference_adapter.py` (LocalCPUStub + NotebookAdapter)
   - `src/avatarpipe/output_validator.py` (image validation)
   - `src/avatarpipe/manifest.py` (manifest writer)
   - `src/avatarpipe/evaluation/*.py` (adherence, diversity, identity)
   - `src/avatarpipe/consent.py` (consent management)
   - `src/avatarpipe/cli.py` (Typer CLI)
5. Write all unit and integration tests (92 tests)
6. Write configuration files, README, SOURCES.md, and this document

---

## Human Review and Testing

All AI-generated code was:
- **Read and understood** line-by-line by the candidate before running
- **Tested** by running the full pytest suite and verifying all 92 tests pass
- **Debugged** (one test failure found and fixed: consent validator error message)
- **Verified** to comply with all §0 constraints (no paid APIs, no Colab, etc.)

The candidate can explain and modify every module listed above. Specifically:
- The rationale for omitting nationality/ethnicity from AvatarSpec
- Why secrets.randbits(32) is used over random.randint
- Why the CPU/GPU split is drawn at the inference_adapter boundary
- How SafetyResult severity levels propagate through full_check()
- What the LocalCPUStubAdapter does and why it must not produce final images

---

## What Was NOT AI-Generated

- The Kaggle notebook execution (run manually by the candidate)
- The actual generated avatar images (produced by SDXL on Kaggle T4)
- The demo video recording
- The official workbook values (filled in by the candidate from actual measurements)
- Live validation session responses (demonstrated live by the candidate)
