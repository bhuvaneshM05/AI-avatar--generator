"""Integration tests for the CPU-side pipeline using LocalCPUStubAdapter.

These tests exercise the full job -> ingest -> manifest chain WITHOUT
touching a GPU. The LocalCPUStubAdapter generates a tiny placeholder image
to prove the plumbing is wired up correctly.

All tests run on plain CPU in < 5 seconds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from avatarpipe.inference_adapter import LocalCPUStubAdapter
from avatarpipe.job_builder import build_job, load_job, save_job
from avatarpipe.manifest import load_manifest, write_manifest
from avatarpipe.output_validator import validate_outputs
from avatarpipe.spec import AgeBand, AvatarSpec, HairSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_spec() -> AvatarSpec:
    return AvatarSpec(
        age_band=AgeBand.adult,
        skin_tone="Fitzpatrick III",
        hair=HairSpec(style="short curly", color="dark brown"),
        attire="business casual blazer",
        background="modern office, soft bokeh",
        seed=42,
    )


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    cfg = tmp_path / "config"
    cfg.mkdir()
    model_registry = {
        "models": {
            "primary": {
                "name": "stable-diffusion-xl-base-1.0",
                "repo": "stabilityai/stable-diffusion-xl-base-1.0",
                "revision": "abc123test",
                "type": "sdxl",
                "recommended_steps": 20,
                "recommended_guidance": 7.5,
                "max_resolution": 1024,
                "license": "CreativeML Open RAIL++-M",
                "commercial_use": False,
            }
        }
    }
    job_config = {
        "defaults": {
            "aspect_ratio": "1:1",
            "model": "primary",
            "inference_steps": 20,
            "guidance_scale": 7.5,
            "output_format": "png",
            "output_width": 1024,
        },
        "provenance": {"accelerator": "local-cpu-stub"},
        "safety": {"on_ambiguous": "flag", "on_blocked": "block", "log_all_results": True},
    }
    (cfg / "model_registry.yaml").write_text(yaml.dump(model_registry))
    (cfg / "default_job_config.yaml").write_text(yaml.dump(job_config))
    return cfg


# ---------------------------------------------------------------------------
# Integration tests: job -> stub inference -> validate -> manifest
# ---------------------------------------------------------------------------

class TestCPUStubPipeline:
    def test_full_pipeline_produces_manifest(self, minimal_spec, config_dir, tmp_path):
        """End-to-end: new-job -> LocalCPUStub inference -> validate -> manifest."""
        # 1. Build and save job
        job = build_job(minimal_spec, config_dir)
        jobs_dir = tmp_path / "jobs"
        job_path = save_job(job, jobs_dir)
        assert job_path.exists()

        # 2. Run LocalCPUStubAdapter
        result_dir = tmp_path / "results"
        adapter = LocalCPUStubAdapter(width=64, height=64)
        fragment = adapter.run(job, result_dir)
        assert "images" in fragment
        assert len(fragment["images"]) > 0

        # 3. Validate outputs
        image_files = [Path(p) for p in fragment["images"]]
        report = validate_outputs(job, image_files, result_dir)
        # Stub generates a valid PNG, so basic checks should pass
        assert report.total_images == 1
        # readable check should pass for a valid PIL-generated image
        assert report.image_results[0].readable

        # 4. Write manifest
        manifest_path = write_manifest(job, image_files, result_dir, validation_report=report)
        assert manifest_path.exists()

        # 5. Load and validate manifest
        manifest = load_manifest(manifest_path)
        assert manifest["job_id"] == job["job_id"]
        assert manifest["synthetic_media_label"] is True
        assert manifest["seed"] == 42

    def test_stub_fragment_has_required_fields(self, minimal_spec, config_dir, tmp_path):
        """LocalCPUStubAdapter result fragment contains all expected keys."""
        job = build_job(minimal_spec, config_dir)
        adapter = LocalCPUStubAdapter()
        fragment = adapter.run(job, tmp_path / "out")
        for key in ("images", "seed", "model_id", "revision", "provenance_route", "generated_at", "image_hashes"):
            assert key in fragment, f"Missing key: {key}"

    def test_stub_provenance_route_is_cpu_stub(self, minimal_spec, config_dir, tmp_path):
        """Stub outputs must be labelled local-cpu-stub, never kaggle."""
        job = build_job(minimal_spec, config_dir)
        adapter = LocalCPUStubAdapter()
        fragment = adapter.run(job, tmp_path / "out")
        assert fragment["provenance_route"] == "local-cpu-stub"

    def test_manifest_contains_safety_result(self, minimal_spec, config_dir, tmp_path):
        """Manifest safety_result field must be present even for clean checks."""
        from avatarpipe.safety import full_check
        job = build_job(minimal_spec, config_dir)
        adapter = LocalCPUStubAdapter()
        fragment = adapter.run(job, tmp_path / "res")
        image_files = [Path(p) for p in fragment["images"]]
        prompt, _ = minimal_spec.to_prompt()
        safety = full_check(prompt, minimal_spec.to_dict())
        manifest_path = write_manifest(job, image_files, tmp_path / "res", safety_result=safety)
        manifest = load_manifest(manifest_path)
        assert "safety_result" in manifest
        assert "passed" in manifest["safety_result"]


class TestCorruptedOutputHandling:
    def test_corrupted_image_fails_validation(self, minimal_spec, config_dir, tmp_path):
        """output_validator must catch a truncated/corrupt image file."""
        job = build_job(minimal_spec, config_dir)
        result_dir = tmp_path / "results"
        result_dir.mkdir()

        # Write a corrupt "image" file (random bytes, not a valid PNG)
        corrupt_img = result_dir / "corrupt.png"
        corrupt_img.write_bytes(b"this is not a valid PNG file \x00\x01\x02")

        report = validate_outputs(job, [corrupt_img], result_dir)
        assert report.total_images == 1
        assert report.failed_images == 1
        assert not report.image_results[0].readable
        assert not report.all_passed

    def test_valid_image_passes_validation(self, minimal_spec, config_dir, tmp_path):
        """A real PIL-generated PNG must pass all validation checks."""
        from PIL import Image
        job = build_job(minimal_spec, config_dir)
        result_dir = tmp_path / "results"
        result_dir.mkdir()

        valid_img = result_dir / "valid.png"
        img = Image.new("RGB", (1024, 1024), color=(100, 150, 200))
        img.save(valid_img)

        report = validate_outputs(job, [valid_img], result_dir)
        assert report.image_results[0].readable
