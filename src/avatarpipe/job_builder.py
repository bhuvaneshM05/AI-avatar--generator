"""job_builder -- translates an AvatarSpec into a portable job bundle.

A job bundle is a self-contained JSON file that includes:
  - The full validated spec (so the GPU notebook never needs to re-validate)
  - Resolved model metadata from the registry
  - The rendered prompt pair
  - All inference parameters
  - Provenance metadata (who built the job, when, on which accelerator)

The bundle is written to jobs/<job_id>.json and uploaded to the remote
accelerator (Kaggle) via `prepare-notebook`.

Design decision: the job bundle is intentionally flat JSON (not YAML) because
JSON is unambiguous -- no implicit type coercions, no anchor/alias pitfalls.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from avatarpipe.spec import AvatarSpec

# Keys that every valid job bundle must contain.
# Checked on load to catch truncated/corrupted files early.
_REQUIRED_JOB_KEYS = {
    "job_id",
    "created_at",
    "spec",
    "model",
    "prompt",
    "negative_prompt",
    "seed",
    "inference_params",
    "provenance_route",
}


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict.

    Raises FileNotFoundError with a helpful message if the file is missing,
    which surfaces clearly in the CLI error handler.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Run from the project root or pass --config-dir explicitly."
        )
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_job(spec: AvatarSpec, config_path: Path) -> dict[str, Any]:
    """Build a complete job bundle dict from a validated AvatarSpec.

    Args:
        spec:        A fully-validated AvatarSpec instance.
        config_path: Path to the directory containing default_job_config.yaml
                     and model_registry.yaml (typically project root / config/).

    Returns:
        A job bundle dict ready to be serialised to JSON via save_job().
    """
    # -- Load config files -----------------------------------------------
    job_cfg = _load_yaml(config_path / "default_job_config.yaml")
    registry = _load_yaml(config_path / "model_registry.yaml")

    # -- Resolve model ---------------------------------------------------
    model_key = job_cfg["defaults"]["model"]  # e.g. "primary"
    if model_key not in registry["models"]:
        raise KeyError(
            f"Model key '{model_key}' not found in model_registry.yaml. "
            f"Available keys: {list(registry['models'].keys())}"
        )
    model_meta = registry["models"][model_key]

    # -- Build inference params ------------------------------------------
    inference_params = {
        "steps": job_cfg["defaults"]["inference_steps"],
        "guidance_scale": job_cfg["defaults"]["guidance_scale"],
        "output_format": job_cfg["defaults"]["output_format"],
        "output_width": job_cfg["defaults"]["output_width"],
        "aspect_ratio": spec.aspect_ratio.value,
    }

    # -- Render prompts --------------------------------------------------
    positive_prompt, negative_prompt = spec.to_prompt()

    # -- Assemble bundle -------------------------------------------------
    job_id = str(uuid.uuid4())
    bundle: dict[str, Any] = {
        "job_id": job_id,
        # ISO 8601 with timezone -- unambiguous for cross-system timestamps
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "spec": spec.to_dict(),
        "model": model_meta,
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        # Seed is already guaranteed non-None by AvatarSpec._assign_seed
        "seed": spec.seed,
        "inference_params": inference_params,
        "provenance_route": job_cfg["provenance"]["accelerator"],
        # Safety config is embedded so the GPU notebook can honour it
        "safety_config": job_cfg.get("safety", {}),
    }
    return bundle


def save_job(job: dict[str, Any], jobs_dir: Path) -> Path:
    """Serialise a job bundle to <jobs_dir>/<job_id>.json.

    Args:
        job:      A bundle dict returned by build_job().
        jobs_dir: Directory to write the JSON file into (created if absent).

    Returns:
        The Path to the written file.
    """
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_path = jobs_dir / f"{job['job_id']}.json"
    with job_path.open("w", encoding="utf-8") as fh:
        # indent=2 for human-readability; sort_keys for deterministic diffs
        json.dump(job, fh, indent=2, sort_keys=True, default=str)
    return job_path


def load_job(job_path: Path) -> dict[str, Any]:
    """Load and minimally validate a job bundle from disk.

    Validates that all required top-level keys are present, which catches
    truncated writes or bundles from an older schema version early.

    Args:
        job_path: Path to the <job_id>.json file.

    Returns:
        The parsed job bundle dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If required keys are missing.
    """
    if not job_path.exists():
        raise FileNotFoundError(f"Job file not found: {job_path}")

    with job_path.open("r", encoding="utf-8") as fh:
        bundle = json.load(fh)

    missing = _REQUIRED_JOB_KEYS - set(bundle.keys())
    if missing:
        raise ValueError(
            f"Job bundle at {job_path} is missing required keys: {sorted(missing)}"
        )
    return bundle
