"""output_validator.py -- Post-generation image and provenance validation.

Validates that files returned from the Kaggle notebook are:
  1. Readable (not corrupted / truncated)
  2. Correct dimensions and aspect ratio (matches the job spec)
  3. Non-blank / non-degenerate (pixel variance check)
  4. Hash-consistent with the result_fragment.json written by the notebook

All checks produce a structured ValidationReport rather than raising
exceptions, so the manifest can record exactly which checks passed/failed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class ImageCheckResult:
    """Result of validation checks for a single image file."""
    path: str
    readable: bool = True
    correct_dimensions: bool = True
    non_blank: bool = True
    hash_consistent: bool = True
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.readable and self.correct_dimensions and self.non_blank and self.hash_consistent


@dataclass
class ValidationReport:
    """Aggregated validation report for all images in a result directory."""
    job_id: str
    total_images: int
    passed_images: int
    failed_images: int
    fragment_present: bool
    image_results: list[ImageCheckResult]

    @property
    def all_passed(self) -> bool:
        return self.failed_images == 0 and self.fragment_present

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "total_images": self.total_images,
            "passed_images": self.passed_images,
            "failed_images": self.failed_images,
            "fragment_present": self.fragment_present,
            "all_passed": self.all_passed,
            "image_results": [
                {
                    "path": r.path,
                    "readable": r.readable,
                    "correct_dimensions": r.correct_dimensions,
                    "non_blank": r.non_blank,
                    "hash_consistent": r.hash_consistent,
                    "errors": r.errors,
                    "passed": r.passed,
                }
                for r in self.image_results
            ],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ASPECT_TO_RATIO: dict[str, float] = {
    "1:1": 1.0,
    "3:4": 3.0 / 4.0,
    "9:16": 9.0 / 16.0,
}

# Tolerance for aspect ratio check (to allow minor rounding in dimensions)
_ASPECT_TOLERANCE = 0.05

# Minimum pixel variance (std dev across all channels) to be considered "non-blank".
# A pure white/black/grey solid fill has variance=0; real images have much higher.
_MIN_VARIANCE = 1.0


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_single_image(
    img_path: Path,
    expected_aspect: str,
    expected_hash: str | None,
) -> ImageCheckResult:
    """Run all validation checks on a single image file."""
    result = ImageCheckResult(path=str(img_path))

    # -- Check 1: readability (not corrupted) ----------------------------
    try:
        img = Image.open(img_path)
        img.verify()  # raises if corrupted
        # Re-open after verify (verify() closes the file)
        img = Image.open(img_path)
        img.load()
    except Exception as exc:
        result.readable = False
        result.errors.append(f"Image unreadable: {exc}")
        # Cannot do further checks on a corrupted image
        return result

    # -- Check 2: dimensions / aspect ratio ------------------------------
    w, h = img.size
    if w == 0 or h == 0:
        result.correct_dimensions = False
        result.errors.append(f"Zero dimension: {w}x{h}")
    else:
        actual_ratio = w / h
        expected_ratio = _ASPECT_TO_RATIO.get(expected_aspect)
        if expected_ratio is not None:
            if abs(actual_ratio - expected_ratio) > _ASPECT_TOLERANCE:
                result.correct_dimensions = False
                result.errors.append(
                    f"Aspect ratio mismatch: got {w}x{h} (ratio={actual_ratio:.3f}), "
                    f"expected ~{expected_aspect} (ratio={expected_ratio:.3f})"
                )

    # -- Check 3: non-blank (pixel variance) -----------------------------
    try:
        import numpy as np
        arr = np.array(img.convert("RGB")).astype(float)
        variance = arr.std()
        if variance < _MIN_VARIANCE:
            result.non_blank = False
            result.errors.append(f"Image appears blank (pixel std={variance:.4f} < {_MIN_VARIANCE})")
    except ImportError:
        # numpy not available; skip variance check gracefully
        pass

    # -- Check 4: hash consistency ---------------------------------------
    if expected_hash is not None:
        actual_hash = _sha256(img_path)
        if actual_hash != expected_hash:
            result.hash_consistent = False
            result.errors.append(
                f"SHA-256 mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
            )

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_outputs(
    job_bundle: dict[str, Any],
    image_files: list[Path],
    result_dir: Path,
) -> ValidationReport:
    """Validate all images in a result directory against the job spec.

    Args:
        job_bundle:  The original job bundle dict (for spec + seed reference).
        image_files: List of image file Paths to validate.
        result_dir:  The directory containing the notebook's outputs
                     (also checked for result_fragment.json).

    Returns:
        A ValidationReport summarising all checks.
    """
    job_id = job_bundle.get("job_id", "unknown")
    expected_aspect = job_bundle.get("spec", {}).get("aspect_ratio", "1:1")

    # Load result_fragment.json to get expected hashes (if present)
    fragment_path = result_dir / "result_fragment.json"
    fragment_present = fragment_path.exists()
    expected_hashes: dict[str, str] = {}
    if fragment_present:
        try:
            with fragment_path.open("r", encoding="utf-8") as fh:
                fragment = json.load(fh)
            expected_hashes = fragment.get("image_hashes", {})
        except Exception:
            pass  # missing hashes = hash_consistent check is skipped

    # Run checks on each image
    image_results: list[ImageCheckResult] = []
    for img_path in image_files:
        expected_hash = expected_hashes.get(img_path.name)
        check = _check_single_image(img_path, expected_aspect, expected_hash)
        image_results.append(check)

    passed = sum(1 for r in image_results if r.passed)
    failed = len(image_results) - passed

    return ValidationReport(
        job_id=job_id,
        total_images=len(image_files),
        passed_images=passed,
        failed_images=failed,
        fragment_present=fragment_present,
        image_results=image_results,
    )
