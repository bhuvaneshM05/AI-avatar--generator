"""AvatarSpec -- Pydantic v2 schema for a single avatar generation request.

This module defines the data model that drives every stage of the pipeline:
prompt construction, safety checks, job bundling, and output validation.

Design constraints (intentional omissions):
  - NO nationality field: nationality is a protected characteristic in many
    jurisdictions and adds no generative value beyond what skin_tone + attire
    already capture. Omitting it reduces discrimination risk at the data-model
    level -- the earliest possible intervention point.
  - NO ethnicity field: same rationale as nationality. The Fitzpatrick scale
    in skin_tone is a dermatological descriptor, not an ethnic identifier.

Sample YAML spec (save as my_avatar.yaml and pass to `avatarpipe new-job`):

    age_band: young_adult
    presentation: feminine
    skin_tone: "Fitzpatrick III"
    hair:
      style: "shoulder-length wavy"
      color: "dark brown"
    attire: "business casual blazer, white shirt"
    background: "modern office, soft bokeh"
    pose: "neutral front-facing"
    aspect_ratio: "1:1"
"""

from __future__ import annotations

import json
import secrets
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class HairSpec(BaseModel):
    """Describes the avatar's hair style and colour.

    Kept as a nested model (rather than a flat string) so that downstream
    prompt templates can independently vary style and colour for diversity
    testing without re-parsing a combined string.
    """

    style: str = Field(
        ...,
        description="Hair style descriptor (e.g. 'short curly', 'long straight')",
        min_length=1,
        max_length=100,
    )
    color: str = Field(
        ...,
        description="Hair colour descriptor (e.g. 'jet black', 'platinum blonde')",
        min_length=1,
        max_length=100,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgeBand(str, Enum):
    """Broad age categories.

    Using bands rather than exact ages:
    1. Avoids generating photorealistic minors with high specificity.
    2. Reduces the precision of the demographic profile, which limits
       re-identification risk when combined with other attributes.
    """
    child = "child"
    teen = "teen"
    young_adult = "young_adult"
    adult = "adult"
    senior = "senior"


class AspectRatio(str, Enum):
    """Supported output aspect ratios.

    Values mirror SDXL's natively-supported ratios to avoid crop artefacts.
    """
    one_to_one = "1:1"
    three_to_four = "3:4"
    nine_to_sixteen = "9:16"


class Presentation(str, Enum):
    """Gender presentation descriptor.

    'unspecified' is the default to prevent the pipeline from making
    assumptions about presentation when the caller has not expressed intent.
    """
    feminine = "feminine"
    masculine = "masculine"
    androgynous = "androgynous"
    unspecified = "unspecified"


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

# Negative prompt applied to every generation. Centralising it here ensures
# consistency across CPU-stub runs and real GPU runs.
_BASE_NEGATIVE_PROMPT = (
    "nsfw, explicit, nudity, violence, gore, ugly, deformed, blurry, "
    "low quality, watermark, signature, text, logo, duplicate, mutation, "
    "bad anatomy, extra limbs, cartoon, anime, illustration, painting"
)

# Aspect-ratio -> SDXL resolution mapping (width x height).
# These are SDXL's recommended native resolutions; non-native sizes cause
# composition artefacts due to the training distribution.
_ASPECT_RESOLUTION: dict[AspectRatio, tuple[int, int]] = {
    AspectRatio.one_to_one: (1024, 1024),
    AspectRatio.three_to_four: (896, 1152),
    AspectRatio.nine_to_sixteen: (768, 1344),
}


def get_resolution(aspect_ratio: AspectRatio) -> tuple[int, int]:
    """Return the (width, height) for a given aspect ratio."""
    return _ASPECT_RESOLUTION[aspect_ratio]


# ---------------------------------------------------------------------------
# Main model
# ---------------------------------------------------------------------------

class AvatarSpec(BaseModel):
    """Complete specification for one avatar generation job.

    Instances of this class are the canonical input to every downstream
    pipeline stage. They are created from YAML/JSON user input, validated
    here, and serialised to the job bundle via to_dict().
    """

    # -- Demographic descriptors ------------------------------------------
    age_band: AgeBand = Field(..., description="Broad age category of the avatar")
    presentation: Presentation = Field(
        Presentation.unspecified,
        description="Gender presentation; defaults to unspecified to avoid assumptions",
    )
    # skin_tone uses Fitzpatrick scale (I-VI) or free-text descriptive phrases.
    # It is a dermatological descriptor, NOT an ethnicity identifier.
    skin_tone: str = Field(
        ...,
        description=(
            "Skin tone descriptor using Fitzpatrick scale (I-VI) or "
            "descriptive text (e.g. 'warm olive'). NOT an ethnicity field."
        ),
        min_length=1,
        max_length=100,
    )
    hair: HairSpec = Field(..., description="Hair style and colour")

    # -- Scene descriptors ------------------------------------------------
    attire: str = Field(
        ...,
        description="Clothing / style descriptor (e.g. 'business casual blazer')",
        max_length=200,
    )
    background: str = Field(
        ...,
        description="Background scene description (e.g. 'modern office, soft bokeh')",
        max_length=200,
    )
    pose: str = Field(
        "neutral front-facing",
        description="Body pose descriptor; defaults to neutral front-facing",
        max_length=100,
    )

    # -- Output config ----------------------------------------------------
    aspect_ratio: AspectRatio = Field(
        AspectRatio.one_to_one,
        description="Output image aspect ratio",
    )

    # -- Reproducibility --------------------------------------------------
    # seed is auto-assigned if None. We use secrets.randbits(32) rather than
    # random.randint because secrets is cryptographically random -- this
    # prevents adversarial seed prediction while still being fully
    # deterministic once assigned (same seed -> same image on same hardware).
    seed: Optional[int] = Field(
        None,
        description=(
            "RNG seed for reproducibility. Auto-assigned via secrets.randbits(32) "
            "if not provided -- ensures uniqueness without predictability."
        ),
        ge=0,
    )

    # -- Consent / reference mode -----------------------------------------
    # reference_images is intentionally a List[Path] (not URLs) to force
    # local pre-processing and consent verification before any data leaves
    # the user's machine.
    reference_images: List[Path] = Field(
        default_factory=list,
        description=(
            "Optional reference images for consented individual-avatar mode. "
            "Requires consent_id to be set."
        ),
    )
    consent_id: Optional[str] = Field(
        None,
        description=(
            "Consent record ID from the consent management system. "
            "MUST be set when reference_images is non-empty."
        ),
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_consent_for_reference_images(self) -> "AvatarSpec":
        """Enforce the consent rule: reference images require a consent ID.

        This is a hard gate -- we never process biometric reference images
        without a valid consent record. Raising here (at schema validation
        time) means the check happens before any file I/O or GPU calls.
        """
        if not self.reference_images:
            return self

        # reference_images is non-empty: consent_id is now required
        if self.consent_id is None:
            raise ValueError(
                "consent_id is required when reference_images is provided. "
                "Obtain a consent record ID from the consent management system first."
            )
        # Also reject empty-string consent IDs -- they pass a None check
        # but are semantically invalid (empty string ≠ valid consent record).
        if self.consent_id.strip() == "":
            raise ValueError(
                "consent_id must be a non-empty string when reference_images is provided. "
                "An empty consent_id is not a valid consent record."
            )
        return self

    @model_validator(mode="after")
    def _assign_seed(self) -> "AvatarSpec":
        """Auto-assign a reproducible seed if none was provided.

        Using secrets.randbits(32) rather than random.randint:
        - Cryptographically random -> not predictable from timestamp or PID
        - 32-bit -> compatible with both SDXL and SD 1.5 seed ranges
        - Assigned here (not at call-site) so the assigned value is
          persisted in to_dict() and the job bundle -- enabling exact replay.
        """
        if self.seed is None:
            self.seed = secrets.randbits(32)
        return self

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def to_prompt(self) -> Tuple[str, str]:
        """Build (positive_prompt, negative_prompt) from this spec.

        The positive prompt is assembled in a deliberate order:
        1. Subject (age + presentation + skin tone + hair)
        2. Attire
        3. Pose
        4. Background / environment
        5. Quality booster tags

        This ordering follows CLIP attention -- earlier tokens receive
        more weight in cross-attention, so subject descriptors take
        precedence over background.

        Returns:
            A 2-tuple of (positive_prompt, negative_prompt) strings.
        """
        age_str = self.age_band.value.replace("_", " ")  # e.g. "young adult"

        # Only include presentation if the caller specified it explicitly
        presentation_str = (
            f"{self.presentation.value} "
            if self.presentation != Presentation.unspecified
            else ""
        )

        subject = (
            f"a {presentation_str}{age_str} person, "
            f"{self.skin_tone} skin tone, "
            f"{self.hair.style} {self.hair.color} hair"
        )

        positive = (
            f"{subject}, "
            f"wearing {self.attire}, "
            f"{self.pose} pose, "
            f"{self.background}, "
            "professional portrait photography, sharp focus, "
            "high resolution, 8k, photorealistic, studio lighting"
        )

        return positive, _BASE_NEGATIVE_PROMPT

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary representation of this spec.

        Path objects are converted to strings so that json.dumps() works
        without a custom encoder -- important for the job bundle.
        """
        raw = self.model_dump()
        # Convert Path objects to strings (Pydantic v2 keeps them as Path)
        raw["reference_images"] = [str(p) for p in self.reference_images]
        # Convert enums to their string values for readability in JSON
        raw["age_band"] = self.age_band.value
        raw["presentation"] = self.presentation.value
        raw["aspect_ratio"] = self.aspect_ratio.value
        return raw
