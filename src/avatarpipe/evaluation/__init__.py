"""Evaluation metrics: adherence, diversity, identity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from avatarpipe.evaluation.diversity import compute_diversity


def run_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    """Run all applicable evaluation metrics on a manifest.

    Returns a dictionary of metric names and formatted scores.
    """
    scores: dict[str, Any] = {}

    # 1. Diversity coverage for this avatar
    div_report = compute_diversity([manifest])
    scores["diversity_coverage_score"] = div_report.get("coverage_score", 0.0)
    scores["attributes_covered"] = div_report.get("summary", "N/A")

    # 2. Spec adherence via CLIP if available and image exists
    img_path_str = manifest.get("output_path")
    prompt = manifest.get("prompt", "")
    if img_path_str and Path(img_path_str).exists() and prompt:
        try:
            from avatarpipe.evaluation.adherence import score_adherence
            adh_score = score_adherence(Path(img_path_str), prompt)
            scores["clip_adherence_similarity"] = adh_score
        except Exception as exc:
            scores["clip_adherence_similarity"] = f"Unavailable ({type(exc).__name__})"
    else:
        scores["clip_adherence_similarity"] = "Image not found on disk"

    scores["synthetic_media_labeled"] = bool(manifest.get("synthetic_media_label", False))
    scores["seed_recorded"] = manifest.get("seed") is not None
    scores["manifest_version"] = manifest.get("manifest_version", "1.0")

    return scores
