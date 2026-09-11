"""safety.py -- Pre-generation content policy checks.

Design decisions:
  - Rule-based (not ML-only) so every rule is auditable and explainable.
    An evaluator can read this file and understand exactly what is blocked.
  - Structured SafetyResult (not just bool) so every check is logged with
    full context -- severity, triggered rules, reason, and the checked text.
  - Three severity levels:
      clean = pass through, no issues detected
      flag  = allow but log a warning (ambiguous / edge cases)
      block = refuse generation, log reason, never silently swallowed
  - Results are ALWAYS written to the manifest, even for clean checks.
    This ensures the audit trail is complete.
  - All regex patterns are compiled at import time for performance.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Severity enum and result model
# ---------------------------------------------------------------------------

class SafetySeverity(str, Enum):
    """Three-level severity scale for safety check results.

    Using str mixin ensures JSON serialisation works without a custom encoder.
    """
    clean = "clean"
    flag = "flag"
    block = "block"


class SafetyResult(BaseModel):
    """Structured result of a safety/policy check.

    Every field is logged to the avatar_manifest.json -- this is intentional
    so that reviewers can audit exactly what was checked and why it passed/failed.
    """
    passed: bool = Field(..., description="True = clean or flag (allowed); False = block (refused)")
    severity: SafetySeverity = Field(..., description="Severity level of the most serious finding")
    flags: List[str] = Field(default_factory=list, description="Names of all triggered rules")
    reason: str = Field(..., description="Human-readable explanation of the result")
    checked_text: str = Field(..., description="The text that was checked (for audit trail)")
    checked_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

# Each rule is a (name, compiled_regex, reason_string) tuple.
# Block rules: any match -> severity=block, passed=False
_BLOCK_RULES: List[tuple[str, re.Pattern, str]] = [
    (
        "explicit_sexual",
        re.compile(r"nude|naked|explicit|pornograph|sexual(?!\s+orientation)|nsfw", re.I),
        "Explicit sexual content is not permitted",
    ),
    (
        "csam",
        re.compile(r"child.*exploit|loli(?!\w)|shota(?!\w)", re.I),
        "Content involving minors in a sexual or exploitative context is not permitted",
    ),
    (
        "real_person_deepfake",
        re.compile(r"real\s+person|photo.*celebrity|deepfake.*celebrity|impersonat", re.I),
        "Non-consented real-person reference or deepfake generation is not permitted",
    ),
    (
        "harmful_instructions",
        re.compile(r"weapon.*blueprint|bomb.*instruct|explosive.*instruct|how\s+to\s+make.*weapon", re.I),
        "Harmful technical instructions are not permitted",
    ),
    (
        "graphic_violence",
        re.compile(r"\bkill\b|\bmurder\b|torture|gore|decapitat|massacre|dismember", re.I),
        "Graphic violence is not permitted",
    ),
]

# Flag rules: any match -> severity=flag, passed=True (allowed but logged)
_FLAG_RULES: List[tuple[str, re.Pattern, str]] = [
    (
        "all_caps_text",
        re.compile(r"[A-Z]{5,}"),
        "Unusual all-caps formatting detected; verify intent",
    ),
]

# Contradictory attire<->background pairs (naive heuristic, not a hard block)
# Each entry is (attire_pattern, background_pattern, reason)
_CONTRADICTORY_PAIRS: List[tuple[re.Pattern, re.Pattern, str]] = [
    (re.compile(r"winter|heavy coat|parka", re.I), re.compile(r"beach|tropical|desert sun", re.I),
     "Attire and background may be climatically contradictory"),
    (re.compile(r"swimsuit|swimwear|bikini", re.I), re.compile(r"snow|arctic|blizzard", re.I),
     "Attire and background may be climatically contradictory"),
    (re.compile(r"tuxedo|evening gown|formal", re.I), re.compile(r"beach|camping|hiking", re.I),
     "Attire and background may be contextually contradictory"),
    (re.compile(r"hazmat|protective suit", re.I), re.compile(r"restaurant|cafe|library", re.I),
     "Attire and background may be contextually contradictory"),
]

# Minimum character count for free-text spec fields before flagging as under-specified
_MIN_FIELD_LENGTH = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_block_rules(text: str) -> tuple[list[str], list[str]]:
    """Run all block rules against text. Returns (triggered_names, reasons)."""
    triggered_names: list[str] = []
    reasons: list[str] = []
    for name, pattern, reason in _BLOCK_RULES:
        if pattern.search(text):
            triggered_names.append(name)
            reasons.append(reason)
    return triggered_names, reasons


def _run_flag_rules(text: str) -> tuple[list[str], list[str]]:
    """Run all flag rules against text. Returns (triggered_names, reasons)."""
    triggered_names: list[str] = []
    reasons: list[str] = []
    for name, pattern, reason in _FLAG_RULES:
        if pattern.search(text):
            triggered_names.append(name)
            reasons.append(reason)
    return triggered_names, reasons


def _worst(a: SafetyResult, b: SafetyResult) -> SafetyResult:
    """Merge two SafetyResults, returning the most severe combined result.

    Precedence: block > flag > clean.
    All triggered flags from both results are accumulated (not de-duplicated)
    to provide a complete audit trail.
    """
    severity_rank = {SafetySeverity.clean: 0, SafetySeverity.flag: 1, SafetySeverity.block: 2}
    if severity_rank[a.severity] >= severity_rank[b.severity]:
        dominant, other = a, b
    else:
        dominant, other = b, a

    merged_flags = list(dict.fromkeys(dominant.flags + other.flags))  # preserve order, deduplicate
    merged_reason = dominant.reason
    if other.reason and other.reason != dominant.reason:
        merged_reason = f"{dominant.reason}; {other.reason}"

    return SafetyResult(
        passed=dominant.passed,
        severity=dominant.severity,
        flags=merged_flags,
        reason=merged_reason,
        checked_text=f"{a.checked_text} | {b.checked_text}",
        checked_at=dominant.checked_at,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_prompt(prompt: str, spec_dict: Optional[dict] = None) -> SafetyResult:
    """Run all safety checks on the resolved prompt text.

    Args:
        prompt:    The fully-resolved positive prompt string.
        spec_dict: Optional raw spec dict for supplemental context checks.

    Returns:
        A SafetyResult describing the outcome.
    """
    # Run block rules first -- they take priority
    blocked_names, blocked_reasons = _run_block_rules(prompt)
    if blocked_names:
        return SafetyResult(
            passed=False,
            severity=SafetySeverity.block,
            flags=blocked_names,
            reason="; ".join(blocked_reasons),
            checked_text=prompt,
        )

    # Run flag rules
    flagged_names, flagged_reasons = _run_flag_rules(prompt)
    if flagged_names:
        return SafetyResult(
            passed=True,
            severity=SafetySeverity.flag,
            flags=flagged_names,
            reason="; ".join(flagged_reasons),
            checked_text=prompt,
        )

    return SafetyResult(
        passed=True,
        severity=SafetySeverity.clean,
        flags=[],
        reason="No issues detected",
        checked_text=prompt,
    )


def check_spec_fields(spec_dict: dict) -> SafetyResult:
    """Check individual spec fields for safety issues and under-specification.

    Running checks on raw spec fields (before prompt resolution) catches
    issues that prompt-template merging might obscure -- e.g. a blocked
    term in the 'background' field that gets embedded in the negative prompt.

    Args:
        spec_dict: The raw spec dictionary (from AvatarSpec.to_dict()).

    Returns:
        A SafetyResult describing the outcome.
    """
    flags: list[str] = []
    reasons: list[str] = []
    severity = SafetySeverity.clean
    passed = True

    # Check all string fields for block rule violations
    str_fields = ["attire", "background", "pose", "skin_tone"]
    for field_name in str_fields:
        value = spec_dict.get(field_name, "") or ""
        blocked_names, blocked_reasons = _run_block_rules(str(value))
        if blocked_names:
            # Escalate to block immediately
            flags.extend([f"{field_name}:{n}" for n in blocked_names])
            reasons.extend(blocked_reasons)
            severity = SafetySeverity.block
            passed = False

    # Check for under-specified fields (flag only)
    for field_name in str_fields:
        value = spec_dict.get(field_name, "") or ""
        if 0 < len(str(value).strip()) < _MIN_FIELD_LENGTH:
            flag_name = f"under_specified_{field_name}"
            flags.append(flag_name)
            reasons.append(f"Field '{field_name}' is very short ({len(str(value).strip())} chars); may produce ambiguous output")
            if severity == SafetySeverity.clean:
                severity = SafetySeverity.flag

    # Check for contradictory attire <-> background
    attire = spec_dict.get("attire", "") or ""
    background = spec_dict.get("background", "") or ""
    for attire_pat, bg_pat, reason in _CONTRADICTORY_PAIRS:
        if attire_pat.search(attire) and bg_pat.search(background):
            flags.append("contradictory_attire_background")
            reasons.append(reason)
            if severity == SafetySeverity.clean:
                severity = SafetySeverity.flag
            break  # one flag is enough for this category

    checked_text = f"spec_fields:{list(spec_dict.keys())}"
    reason_str = "; ".join(reasons) if reasons else "No issues detected"

    return SafetyResult(
        passed=passed,
        severity=severity,
        flags=flags,
        reason=reason_str,
        checked_text=checked_text,
    )


def full_check(prompt: str, spec_dict: dict) -> SafetyResult:
    """Run both check_prompt and check_spec_fields, returning the worst result.

    This is the primary entry point for the CLI and notebook -- it guarantees
    both the raw spec fields AND the resolved prompt are checked.

    Args:
        prompt:    The fully-resolved positive prompt string.
        spec_dict: The raw spec dictionary (from AvatarSpec.to_dict()).

    Returns:
        The most severe SafetyResult from both checks, with all flags merged.
    """
    prompt_result = check_prompt(prompt, spec_dict)
    spec_result = check_spec_fields(spec_dict)
    return _worst(prompt_result, spec_result)
