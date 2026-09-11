"""Unit tests for avatarpipe.spec -- AvatarSpec schema and validation.

All tests are pure-Python (no GPU, no real file I/O beyond tmp_path).
Target runtime: < 2 seconds on any CPU-only machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from avatarpipe.spec import AgeBand, AspectRatio, AvatarSpec, HairSpec, Presentation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_kwargs() -> dict:
    """Minimum required fields for a valid AvatarSpec."""
    return {
        "age_band": AgeBand.adult,
        "skin_tone": "Fitzpatrick III",
        "hair": HairSpec(style="short curly", color="dark brown"),
        "attire": "business casual blazer",
        "background": "modern office, soft bokeh",
    }


# ---------------------------------------------------------------------------
# Valid spec creation
# ---------------------------------------------------------------------------

class TestValidSpecCreation:
    def test_minimal_spec_is_valid(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.age_band == AgeBand.adult

    def test_all_fields_accepted(self):
        spec = AvatarSpec(
            age_band=AgeBand.young_adult,
            presentation=Presentation.feminine,
            skin_tone="warm olive",
            hair=HairSpec(style="long wavy", color="jet black"),
            attire="casual t-shirt",
            background="park, golden hour",
            pose="three-quarter turn",
            aspect_ratio=AspectRatio.three_to_four,
            seed=42,
        )
        assert spec.seed == 42
        assert spec.presentation == Presentation.feminine

    def test_default_presentation_is_unspecified(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.presentation == Presentation.unspecified

    def test_default_pose(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.pose == "neutral front-facing"

    def test_default_aspect_ratio(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.aspect_ratio == AspectRatio.one_to_one


# ---------------------------------------------------------------------------
# Seed behaviour
# ---------------------------------------------------------------------------

class TestSeedAssignment:
    def test_auto_seed_assigned_when_none(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.seed is not None
        assert isinstance(spec.seed, int)
        assert spec.seed >= 0

    def test_auto_seeds_are_unique(self):
        seeds = {AvatarSpec(**_minimal_kwargs()).seed for _ in range(20)}
        assert len(seeds) > 1, "All auto-assigned seeds identical -- RNG broken"

    def test_explicit_seed_preserved(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "seed": 12345})
        assert spec.seed == 12345

    def test_seed_zero_is_valid(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "seed": 0})
        assert spec.seed == 0


# ---------------------------------------------------------------------------
# Consent / reference image validation
# ---------------------------------------------------------------------------

class TestConsentValidation:
    def test_reference_images_without_consent_id_raises(self, tmp_path):
        dummy = tmp_path / "face.jpg"
        dummy.write_bytes(b"fake")
        with pytest.raises(ValidationError, match="consent_id is required"):
            AvatarSpec(**{**_minimal_kwargs(), "reference_images": [dummy]})

    def test_reference_images_with_empty_consent_id_raises(self, tmp_path):
        dummy = tmp_path / "face.jpg"
        dummy.write_bytes(b"fake")
        with pytest.raises(ValidationError, match="non-empty string"):
            AvatarSpec(**{**_minimal_kwargs(), "reference_images": [dummy], "consent_id": ""})

    def test_reference_images_with_valid_consent_id_passes(self, tmp_path):
        dummy = tmp_path / "face.jpg"
        dummy.write_bytes(b"fake")
        spec = AvatarSpec(**{**_minimal_kwargs(), "reference_images": [dummy], "consent_id": "consent-abc-123"})
        assert spec.consent_id == "consent-abc-123"
        assert len(spec.reference_images) == 1

    def test_no_reference_images_consent_id_optional(self):
        spec = AvatarSpec(**_minimal_kwargs())
        assert spec.consent_id is None


# ---------------------------------------------------------------------------
# to_prompt()
# ---------------------------------------------------------------------------

class TestToPrompt:
    def test_returns_tuple_of_two_strings(self):
        spec = AvatarSpec(**_minimal_kwargs())
        result = spec.to_prompt()
        assert isinstance(result, tuple) and len(result) == 2
        assert all(isinstance(s, str) for s in result)

    def test_positive_prompt_contains_age_band(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "age_band": AgeBand.senior})
        positive, _ = spec.to_prompt()
        assert "senior" in positive

    def test_positive_prompt_contains_skin_tone(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "skin_tone": "Fitzpatrick V"})
        positive, _ = spec.to_prompt()
        assert "Fitzpatrick V" in positive

    def test_positive_prompt_contains_hair_style(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "hair": HairSpec(style="braided", color="auburn")})
        positive, _ = spec.to_prompt()
        assert "braided" in positive

    def test_positive_prompt_contains_attire(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "attire": "red evening gown"})
        positive, _ = spec.to_prompt()
        assert "red evening gown" in positive

    def test_negative_prompt_contains_nsfw(self):
        _, negative = AvatarSpec(**_minimal_kwargs()).to_prompt()
        assert "nsfw" in negative

    def test_unspecified_presentation_not_in_prompt(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "presentation": Presentation.unspecified})
        positive, _ = spec.to_prompt()
        assert "unspecified" not in positive

    def test_specified_presentation_appears_in_prompt(self):
        spec = AvatarSpec(**{**_minimal_kwargs(), "presentation": Presentation.masculine})
        positive, _ = spec.to_prompt()
        assert "masculine" in positive


# ---------------------------------------------------------------------------
# to_dict() / serialisation
# ---------------------------------------------------------------------------

class TestToDict:
    def test_to_dict_is_json_serialisable(self):
        spec = AvatarSpec(**_minimal_kwargs())
        serialised = json.dumps(spec.to_dict())
        assert len(serialised) > 10

    def test_to_dict_enum_values_are_strings(self):
        d = AvatarSpec(**_minimal_kwargs()).to_dict()
        assert isinstance(d["age_band"], str)
        assert isinstance(d["presentation"], str)
        assert isinstance(d["aspect_ratio"], str)

    def test_to_dict_reference_images_are_strings(self, tmp_path):
        dummy = tmp_path / "img.png"
        dummy.write_bytes(b"fake")
        spec = AvatarSpec(**{**_minimal_kwargs(), "reference_images": [dummy], "consent_id": "c-001"})
        d = spec.to_dict()
        assert all(isinstance(p, str) for p in d["reference_images"])


# ---------------------------------------------------------------------------
# Enum round-trips
# ---------------------------------------------------------------------------

class TestEnumRoundTrips:
    @pytest.mark.parametrize("band", list(AgeBand))
    def test_age_band_roundtrip(self, band):
        spec = AvatarSpec(**{**_minimal_kwargs(), "age_band": band})
        assert AgeBand(spec.to_dict()["age_band"]) == band

    @pytest.mark.parametrize("pres", list(Presentation))
    def test_presentation_roundtrip(self, pres):
        spec = AvatarSpec(**{**_minimal_kwargs(), "presentation": pres})
        assert Presentation(spec.to_dict()["presentation"]) == pres

    @pytest.mark.parametrize("ar", list(AspectRatio))
    def test_aspect_ratio_roundtrip(self, ar):
        spec = AvatarSpec(**{**_minimal_kwargs(), "aspect_ratio": ar})
        assert AspectRatio(spec.to_dict()["aspect_ratio"]) == ar


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

class TestYamlLoading:
    def test_spec_loads_from_yaml_file(self, tmp_path):
        data = {
            "age_band": "adult",
            "presentation": "feminine",
            "skin_tone": "Fitzpatrick II",
            "hair": {"style": "bob cut", "color": "chestnut"},
            "attire": "casual hoodie",
            "background": "coffee shop",
        }
        yf = tmp_path / "spec.yaml"
        yf.write_text(yaml.dump(data), encoding="utf-8")
        with yf.open() as fh:
            raw = yaml.safe_load(fh)
        spec = AvatarSpec(**raw)
        assert spec.age_band == AgeBand.adult
        assert spec.skin_tone == "Fitzpatrick II"
