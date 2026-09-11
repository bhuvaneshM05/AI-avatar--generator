"""diversity.py -- Coverage/diversity metrics across the avatar attribute matrix.

Measures how well a set of generated avatars covers the specified attribute
space. Used to verify that the 6 baseline avatars demonstrate meaningful
diversity rather than clustering around similar appearances.

Diversity score = (unique attribute values covered) / (total required attribute values)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Required attribute dimensions and their minimum expected coverage
REQUIRED_DIMENSIONS = {
    "age_band": {"child", "teen", "young_adult", "adult", "senior"},
    "presentation": {"feminine", "masculine", "androgynous", "unspecified"},
    "skin_tone_category": {"very_light", "light", "medium", "olive", "brown", "dark"},
}

# Fitzpatrick scale -> category mapping for skin tone normalisation
FITZPATRICK_MAP = {
    "I": "very_light", "II": "light", "III": "medium",
    "IV": "olive", "V": "brown", "VI": "dark",
}


def _categorise_skin_tone(skin_tone: str) -> str:
    """Map a free-text skin_tone value to a normalised category.

    Falls back to 'other' if the value doesn't match known categories.
    """
    tone = skin_tone.strip()
    # Check Fitzpatrick notation (e.g. "Fitzpatrick III" or "III")
    for roman, category in FITZPATRICK_MAP.items():
        if roman in tone:
            return category
    # Descriptive keywords
    tone_lower = tone.lower()
    if any(k in tone_lower for k in ("very light", "pale", "fair")):
        return "very_light"
    if any(k in tone_lower for k in ("light",)):
        return "light"
    if any(k in tone_lower for k in ("medium", "beige")):
        return "medium"
    if any(k in tone_lower for k in ("olive", "tan")):
        return "olive"
    if any(k in tone_lower for k in ("brown", "warm")):
        return "brown"
    if any(k in tone_lower for k in ("dark", "deep")):
        return "dark"
    return "other"


def compute_diversity(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute diversity coverage across a set of avatar manifests.

    Args:
        manifests: List of loaded avatar_manifest.json dicts.

    Returns:
        Dict with:
          coverage_per_dimension: {dimension: {covered_values}, ...}
          coverage_score: float in [0, 1]
          total_avatars: int
          summary: human-readable description
    """
    if not manifests:
        return {"error": "No manifests provided", "coverage_score": 0.0}

    coverage: dict[str, set] = {dim: set() for dim in REQUIRED_DIMENSIONS}

    for manifest in manifests:
        spec = manifest.get("spec", {})

        # age_band
        age = spec.get("age_band")
        if age:
            coverage["age_band"].add(age)

        # presentation
        pres = spec.get("presentation")
        if pres:
            coverage["presentation"].add(pres)

        # skin_tone (normalised)
        tone = spec.get("skin_tone", "")
        if tone:
            coverage["skin_tone_category"].add(_categorise_skin_tone(tone))

    # Compute coverage score
    total_required = sum(len(v) for v in REQUIRED_DIMENSIONS.values())
    total_covered = sum(len(coverage[dim]) for dim in REQUIRED_DIMENSIONS)
    score = total_covered / total_required if total_required > 0 else 0.0

    return {
        "coverage_per_dimension": {
            dim: sorted(coverage[dim]) for dim in REQUIRED_DIMENSIONS
        },
        "required_per_dimension": {
            dim: sorted(REQUIRED_DIMENSIONS[dim]) for dim in REQUIRED_DIMENSIONS
        },
        "coverage_score": round(score, 4),
        "total_avatars": len(manifests),
        "summary": (
            f"{total_covered}/{total_required} attribute slots covered "
            f"across {len(manifests)} avatars (score={score:.2%})"
        ),
    }
