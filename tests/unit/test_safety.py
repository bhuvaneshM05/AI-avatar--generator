"""Unit tests for avatarpipe.safety -- content policy checks.

All tests are pure-Python, no GPU, no network. Target runtime < 1 second.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from avatarpipe.safety import (
    SafetyResult,
    SafetySeverity,
    check_prompt,
    check_spec_fields,
    full_check,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _clean_spec() -> dict:
    return {
        "age_band": "adult",
        "skin_tone": "Fitzpatrick III",
        "attire": "business casual blazer",
        "background": "modern office",
        "pose": "neutral front-facing",
    }


# ---------------------------------------------------------------------------
# check_prompt tests
# ---------------------------------------------------------------------------

class TestCheckPrompt:
    def test_clean_prompt_passes(self):
        result = check_prompt("a professional portrait of an adult person, business attire")
        assert result.passed is True
        assert result.severity == SafetySeverity.clean

    def test_explicit_content_blocked(self):
        result = check_prompt("a nude portrait of a person")
        assert result.passed is False
        assert result.severity == SafetySeverity.block
        assert "explicit_sexual" in result.flags

    def test_nsfw_blocked(self):
        result = check_prompt("nsfw portrait photo")
        assert result.passed is False
        assert result.severity == SafetySeverity.block

    def test_violence_blocked(self):
        result = check_prompt("a person covered in gore and blood")
        assert result.passed is False
        assert result.severity == SafetySeverity.block
        assert "graphic_violence" in result.flags

    def test_deepfake_celebrity_blocked(self):
        result = check_prompt("photo of celebrity deepfake portrait")
        assert result.passed is False
        assert result.severity == SafetySeverity.block

    def test_bomb_instructions_blocked(self):
        result = check_prompt("bomb instructions in the background text")
        assert result.passed is False
        assert result.severity == SafetySeverity.block

    def test_blocked_has_passed_false(self):
        result = check_prompt("explicit sexual content")
        assert result.passed is False

    def test_checked_text_preserved(self):
        text = "a professional business portrait"
        result = check_prompt(text)
        assert text in result.checked_text

    def test_multiple_flags_accumulated(self):
        # A prompt that triggers multiple block rules
        result = check_prompt("nude portrait with gore and violence")
        assert len(result.flags) >= 2

    def test_all_caps_text_flagged(self):
        result = check_prompt("A VERY LOUD PROMPT WITH LOTS OF CAPS")
        assert result.severity == SafetySeverity.flag
        assert result.passed is True  # flag = allowed but warned

    def test_flag_has_passed_true(self):
        result = check_prompt("ALLCAPS TEXT HERE portrait")
        assert result.passed is True
        assert result.severity == SafetySeverity.flag

    def test_safety_result_is_serializable(self):
        result = check_prompt("a professional portrait")
        d = result.model_dump()
        # Should not raise
        serialised = json.dumps(d, default=str)
        assert "passed" in serialised

    def test_checked_at_is_datetime(self):
        result = check_prompt("test")
        assert isinstance(result.checked_at, datetime)


# ---------------------------------------------------------------------------
# check_spec_fields tests
# ---------------------------------------------------------------------------

class TestCheckSpecFields:
    def test_clean_spec_passes(self):
        result = check_spec_fields(_clean_spec())
        assert result.passed is True

    def test_ambiguous_spec_flagged(self):
        """Very short skin_tone (< 3 chars) should trigger a flag."""
        spec = {**_clean_spec(), "skin_tone": "ab"}
        result = check_spec_fields(spec)
        assert result.severity == SafetySeverity.flag
        assert result.passed is True

    def test_check_spec_fields_on_missing_fields(self):
        """Empty attire field should trigger an under-specified flag."""
        spec = {**_clean_spec(), "attire": "x"}  # 1 char = under-specified
        result = check_spec_fields(spec)
        assert result.severity == SafetySeverity.flag

    def test_blocked_content_in_spec_field_blocks(self):
        """Block rule triggered in a raw spec field should block."""
        spec = {**_clean_spec(), "background": "explicit nudity scene"}
        result = check_spec_fields(spec)
        assert result.passed is False
        assert result.severity == SafetySeverity.block

    def test_contradictory_attire_background_flagged(self):
        spec = {**_clean_spec(), "attire": "winter parka", "background": "tropical beach"}
        result = check_spec_fields(spec)
        assert result.severity == SafetySeverity.flag
        assert "contradictory_attire_background" in result.flags


# ---------------------------------------------------------------------------
# full_check tests
# ---------------------------------------------------------------------------

class TestFullCheck:
    def test_unsafe_request_blocked(self):
        """Simulate a full_check on an obviously unsafe spec + prompt."""
        spec = {**_clean_spec(), "attire": "nothing, nude"}
        prompt = "a nude person in explicit pose"
        result = full_check(prompt, spec)
        assert result.passed is False
        assert result.severity == SafetySeverity.block

    def test_clean_full_check_baseline(self):
        spec = _clean_spec()
        prompt = "a professional adult person, business casual blazer, modern office, photorealistic"
        result = full_check(prompt, spec)
        assert result.passed is True

    def test_block_takes_precedence_over_flag(self):
        """When prompt is blocked but spec is only flagged, result is block."""
        spec = {**_clean_spec(), "skin_tone": "ab"}  # flag
        prompt = "explicit nude portrait"  # block
        result = full_check(prompt, spec)
        assert result.severity == SafetySeverity.block
        assert result.passed is False

    def test_model_dump_completeness(self):
        result = full_check("a person in a park", _clean_spec())
        d = result.model_dump()
        for key in ("passed", "severity", "flags", "reason", "checked_text", "checked_at"):
            assert key in d
