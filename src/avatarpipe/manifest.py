"""manifest.py -- avatar_manifest.json writer and reader.

The avatar manifest is the single ground-truth record for a completed
avatar generation run. It merges:
  - The original job spec (what was requested)
  - The inference result fragment (what was generated, where, with what seed)
  - The safety check result (pre-generation policy check outcome)
  - The validation report (post-generation image quality checks)
  - Provenance metadata (route, timestamps, run IDs)

Design decision: one manifest file per IMAGE (not per job) so that batch
jobs (future: multiple images per job) produce independently queryable records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Keys required in a valid avatar_manifest.json
REQUIRED_MANIFEST_KEYS = {
    "manifest_version",
    "job_id",
    "spec",
    "seed",
    "model_id",
    "revision",
    "prompt",
    "negative_prompt",
    "provenance",
    "safety_result",
    "synthetic_media_label",
    "output_path",
    "image_hash",
}

MANIFEST_VERSION = "1.0"


def write_manifest(
    job_bundle: dict[str, Any],
    image_files: list[Path],
    result_dir: Path,
    validation_report: Optional[Any] = None,
    safety_result: Optional[Any] = None,
    result_fragment: Optional[dict] = None,
) -> Path:
    """Build and write avatar_manifest.json to result_dir.

    One manifest is written covering the first (primary) image in image_files.
    For multi-image batches, call this function once per image.

    Args:
        job_bundle:       The original job bundle dict.
        image_files:      List of validated image Paths.
        result_dir:       Output directory (manifest written here).
        validation_report: ValidationReport instance or dict (optional).
        safety_result:    SafetyResult instance or dict (optional).
        result_fragment:  Result fragment from the notebook (optional).

    Returns:
        Path to the written avatar_manifest.json.
    """
    if not image_files:
        raise ValueError("Cannot write manifest: no image files provided")

    primary_image = image_files[0]

    # -- Compute image hash ----------------------------------------------
    import hashlib
    h = hashlib.sha256()
    with primary_image.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    image_hash = h.hexdigest()

    # -- Resolve provenance from result_fragment or job_bundle ----------
    frag = result_fragment or {}
    provenance = {
        "route": frag.get("provenance_route", job_bundle.get("provenance_route", "unknown")),
        "generated_at": frag.get("generated_at", datetime.now(tz=timezone.utc).isoformat()),
        "job_id": job_bundle.get("job_id"),
        "notebook": "notebooks/inference_kaggle.ipynb",
    }

    # -- Serialise safety result ----------------------------------------
    if safety_result is not None:
        if hasattr(safety_result, "model_dump"):
            safety_dict = safety_result.model_dump(mode="json")
        else:
            safety_dict = safety_result
    else:
        safety_dict = {"passed": True, "severity": "clean", "flags": [], "reason": "Not checked"}

    # -- Serialise validation report ------------------------------------
    if validation_report is not None:
        if hasattr(validation_report, "to_dict"):
            validation_dict = validation_report.to_dict()
        elif isinstance(validation_report, dict):
            validation_dict = validation_report
        else:
            validation_dict = {"validated": False}
    else:
        validation_dict = {"validated": False}

    # -- Build manifest --------------------------------------------------
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "job_id": job_bundle.get("job_id"),
        "spec": job_bundle.get("spec", {}),
        "seed": frag.get("seed", job_bundle.get("seed")),
        "model_id": frag.get("model_id", job_bundle.get("model", {}).get("name", "unknown")),
        "revision": frag.get("revision", job_bundle.get("model", {}).get("revision", "unknown")),
        "prompt": job_bundle.get("prompt", ""),
        "negative_prompt": job_bundle.get("negative_prompt", ""),
        "provenance": provenance,
        "safety_result": safety_dict,
        # synthetic_media_label: ALWAYS True for AI-generated images.
        # This field exists to make the synthetic nature machine-readable
        # for any downstream system that processes these files.
        "synthetic_media_label": True,
        "output_path": str(primary_image.resolve()),
        "image_hash": image_hash,
        "validation_report": validation_dict,
        "all_images": [str(p.resolve()) for p in image_files],
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # -- Write to disk ---------------------------------------------------
    manifest_path = result_dir / "avatar_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True, default=str)

    return manifest_path


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and validate an avatar_manifest.json.

    Args:
        manifest_path: Path to the manifest file.

    Returns:
        The parsed manifest dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If required keys are missing.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
    if missing:
        raise ValueError(f"Manifest missing required keys: {sorted(missing)}")

    return manifest
