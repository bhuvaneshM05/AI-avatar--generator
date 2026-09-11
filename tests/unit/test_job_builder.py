"""Unit tests for avatarpipe.job_builder.

Uses tmp_path for all file I/O and a minimal config fixture that mirrors
the real config/ YAML files -- no real filesystem config required.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import yaml

from avatarpipe.job_builder import build_job, load_job, save_job
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
    )


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Create a minimal config directory with both YAML files."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

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
    (cfg_dir / "model_registry.yaml").write_text(yaml.dump(model_registry), encoding="utf-8")

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
    (cfg_dir / "default_job_config.yaml").write_text(yaml.dump(job_config), encoding="utf-8")

    return cfg_dir


# ---------------------------------------------------------------------------
# build_job tests
# ---------------------------------------------------------------------------

class TestBuildJob:
    def test_returns_dict_with_required_keys(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        required = {"job_id", "created_at", "spec", "model", "prompt", "negative_prompt", "seed", "inference_params", "provenance_route"}
        assert required.issubset(set(job.keys()))

    def test_job_id_is_valid_uuid(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        # Will raise ValueError if not a valid UUID
        parsed = uuid.UUID(job["job_id"])
        assert str(parsed) == job["job_id"]

    def test_seed_matches_spec_seed(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        assert job["seed"] == minimal_spec.seed

    def test_prompt_is_string(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        assert isinstance(job["prompt"], str)
        assert len(job["prompt"]) > 10

    def test_negative_prompt_is_string(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        assert isinstance(job["negative_prompt"], str)

    def test_spec_embedded_in_bundle(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        assert job["spec"]["age_band"] == minimal_spec.age_band.value

    def test_model_resolved_from_registry(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        assert job["model"]["name"] == "stable-diffusion-xl-base-1.0"

    def test_inference_params_present(self, minimal_spec, config_dir):
        job = build_job(minimal_spec, config_dir)
        params = job["inference_params"]
        assert "steps" in params
        assert "guidance_scale" in params

    def test_created_at_is_iso_string(self, minimal_spec, config_dir):
        from datetime import datetime
        job = build_job(minimal_spec, config_dir)
        # Should parse without error
        dt = datetime.fromisoformat(job["created_at"])
        assert dt.tzinfo is not None  # timezone-aware


# ---------------------------------------------------------------------------
# save_job / load_job tests
# ---------------------------------------------------------------------------

class TestSaveLoadJob:
    def test_save_creates_file(self, minimal_spec, config_dir, tmp_path):
        job = build_job(minimal_spec, config_dir)
        jobs_dir = tmp_path / "jobs"
        job_path = save_job(job, jobs_dir)
        assert job_path.exists()
        assert job_path.suffix == ".json"

    def test_save_filename_contains_job_id(self, minimal_spec, config_dir, tmp_path):
        job = build_job(minimal_spec, config_dir)
        jobs_dir = tmp_path / "jobs"
        job_path = save_job(job, jobs_dir)
        assert job["job_id"] in job_path.name

    def test_load_round_trips(self, minimal_spec, config_dir, tmp_path):
        job = build_job(minimal_spec, config_dir)
        jobs_dir = tmp_path / "jobs"
        job_path = save_job(job, jobs_dir)
        loaded = load_job(job_path)
        assert loaded["job_id"] == job["job_id"]
        assert loaded["seed"] == job["seed"]

    def test_load_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_job(tmp_path / "nonexistent.json")

    def test_load_missing_keys_raises_value_error(self, tmp_path):
        bad_job = {"job_id": "x", "created_at": "y"}  # missing required keys
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad_job))
        with pytest.raises(ValueError, match="missing required keys"):
            load_job(bad_path)
