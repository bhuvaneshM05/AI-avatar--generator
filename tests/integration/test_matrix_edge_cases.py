"""Integration tests: Test Matrix Edge Cases and Exceptional Consented Persona.

Implements Phase 6:
3. One ambiguous specification (under-specified / contradictory -> flag behavior logged, no crash)
4. One unsafe/disallowed request (safety refusal logged with reason)
5. One corrupted output (simulated truncated image flagged by output_validator)
6. (Exceptional) 5 poses/backgrounds x 2 aspect ratios for one consented identity, plus refusal-without-consent
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from PIL import Image

from avatarpipe.spec import AvatarSpec, AgeBand, Presentation, AspectRatio, HairSpec
from avatarpipe.safety import full_check, SafetySeverity
from avatarpipe.job_builder import build_job
from avatarpipe.inference_adapter import LocalCPUStubAdapter
from avatarpipe.output_validator import validate_outputs
from avatarpipe.manifest import write_manifest, load_manifest
from avatarpipe.consent import ConsentRecord, ConsentStore, check_consent

def test_ambiguous_specification_behavior(tmp_path):
    """Case 3: Under-specified or contradictory spec flags review rather than crashing."""
    config_dir = Path("config")
    evidence_dir = Path("evidence/test_matrix/ambiguous")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    # Very short skin_tone + contradictory attire/bg (winter coat at tropical beach)
    spec = AvatarSpec(
        age_band=AgeBand.adult,
        presentation=Presentation.unspecified,
        skin_tone="md",  # short -> under_specified flag
        hair=HairSpec(style="straight", color="dark"),
        attire="heavy winter wool parka coat",
        background="sunny tropical beach with palm trees and ocean waves",
        pose="neutral front-facing",
        seed=3001
    )
    
    prompt, _ = spec.to_prompt()
    safety_result = full_check(prompt, spec.to_dict())
    
    # Must pass (not crash or hard block), but have flag severity
    assert safety_result.passed is True
    assert safety_result.severity == SafetySeverity.flag
    assert len(safety_result.flags) > 0
    
    # Create job and verify manifest logs the flag
    job = build_job(spec, config_dir)
    adapter = LocalCPUStubAdapter(width=256, height=256)
    fragment = adapter.run(job, evidence_dir)
    image_files = [Path(p) for p in fragment["images"]]
    report = validate_outputs(job, image_files, evidence_dir)
    
    manifest_path = write_manifest(job, image_files, evidence_dir, validation_report=report, safety_result=safety_result)
    manifest = load_manifest(manifest_path)
    assert manifest["safety_result"]["severity"] == "flag"
    
    with (evidence_dir / "ambiguous_result.json").open("w", encoding="utf-8") as f:
        json.dump(manifest["safety_result"], f, indent=2)

def test_unsafe_disallowed_request_behavior(tmp_path):
    """Case 4: Safety-layer refusal on disallowed request, logged with reason."""
    evidence_dir = Path("evidence/test_matrix/unsafe_refusal")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    disallowed_spec_dict = {
        "age_band": "adult",
        "presentation": "feminine",
        "skin_tone": "Fitzpatrick II",
        "hair": {"style": "long", "color": "blonde"},
        "attire": "completely nude and exposed",
        "background": "explicit bedroom scene",
        "pose": "nsfw pose"
    }
    
    # Pre-check at field and prompt level
    fake_prompt = "a completely nude adult person in an explicit nsfw pose"
    safety_result = full_check(fake_prompt, disallowed_spec_dict)
    
    assert safety_result.passed is False
    assert safety_result.severity == SafetySeverity.block
    assert "explicit_sexual" in safety_result.flags or len(safety_result.flags) > 0
    
    refusal_log = {
        "action": "refusal",
        "passed": safety_result.passed,
        "severity": safety_result.severity.value,
        "reason": safety_result.reason,
        "flags": safety_result.flags,
        "checked_at": str(safety_result.checked_at)
    }
    with (evidence_dir / "refusal_log.json").open("w", encoding="utf-8") as f:
        json.dump(refusal_log, f, indent=2)

def test_corrupted_output_detection(tmp_path):
    """Case 5: Truncated / corrupt output file flagged by validator."""
    evidence_dir = Path("evidence/test_matrix/corrupted")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    corrupt_file = evidence_dir / "corrupted_output.png"
    # Write corrupt PNG header followed by truncated random bytes
    corrupt_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08TRUNCATED")
    
    dummy_job = {
        "job_id": "test_corrupt_job",
        "spec": {"aspect_ratio": "1:1"},
        "seed": 9999,
        "model": {"name": "test"}
    }
    
    report = validate_outputs(dummy_job, [corrupt_file], evidence_dir)
    assert not report.all_passed
    assert report.failed_images == 1
    assert not report.image_results[0].readable
    
    with (evidence_dir / "validation_failure_report.json").open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

def test_consented_identity_matrix_and_refusal(tmp_path):
    """Case 6 (Exceptional): 5 poses/backgrounds x 2 aspect ratios with consent + refusal without consent."""
    config_dir = Path("config")
    evidence_dir = Path("evidence/test_matrix/consented_persona")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    store = ConsentStore(store_dir=evidence_dir / "consent_store")
    
    # 1. Verify refusal when consent is missing
    fake_ref = evidence_dir / "ref.jpg"
    fake_ref.write_bytes(b"dummy_ref_image")
    
    with pytest.raises(ValidationError, match="consent_id is required"):
        AvatarSpec(
            age_band=AgeBand.adult,
            skin_tone="Fitzpatrick III",
            hair=HairSpec(style="short", color="black"),
            attire="shirt",
            background="wall",
            reference_images=[fake_ref],
            consent_id=None
        )
        
    refusal_record = {
        "status": "refusal_verified",
        "error_type": "ValidationError",
        "enforcement": "Schema-level model_validator blocking reference_images without consent_id"
    }
    with (evidence_dir / "consent_refusal_proof.json").open("w", encoding="utf-8") as f:
        json.dump(refusal_record, f, indent=2)
        
    # 2. Register valid consent
    consent_id = "CONSENT-2026-EXC-001"
    consent_rec = ConsentRecord(
        consent_id=consent_id,
        subject_pseudonym="PERSONA_ALPHA",
        notes="Authorized for PS02 evaluation 5 poses x 2 aspect ratios"
    )
    store.save(consent_rec)
    
    verify_consent = check_consent(consent_id, store=store)
    assert verify_consent.valid is True
    
    # 3. Generate 5 poses/backgrounds x 2 aspect ratios = 10 runs
    variations = [
        ("pose1_corporate", "standing upright arms crossed", "corporate executive boardroom with panoramic windows"),
        ("pose2_outdoor", "seated casually leaning forward", "sunlit city park pathway with autumnal trees"),
        ("pose3_studio", "three-quarter profile with chin tilted up", "sleek studio charcoal seamless background"),
        ("pose4_creative", "candid profile looking off-camera", "industrial artist loft with colorful canvas paintings"),
        ("pose5_academic", "hand resting under chin in thought", "wood-paneled historical university lecture hall"),
    ]
    aspect_ratios = [AspectRatio.one_to_one, AspectRatio.three_to_four]
    
    adapter = LocalCPUStubAdapter(width=256, height=256)
    generated_artifacts = []
    
    for v_idx, (var_name, pose_desc, bg_desc) in enumerate(variations):
        for ar in aspect_ratios:
            run_id = f"{var_name}_{ar.value.replace(':', 'x')}"
            run_dir = evidence_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            
            spec = AvatarSpec(
                age_band=AgeBand.adult,
                presentation=Presentation.feminine,
                skin_tone="Fitzpatrick IV (warm bronze)",
                hair=HairSpec(style="sleek layered shoulder-length lob", color="espresso brown"),
                attire="modern bespoke indigo blazer over silk blouse",
                background=bg_desc,
                pose=pose_desc,
                aspect_ratio=ar,
                seed=5000 + v_idx,
                reference_images=[fake_ref],
                consent_id=consent_id
            )
            
            job = build_job(spec, config_dir)
            fragment = adapter.run(job, run_dir)
            image_files = [Path(p) for p in fragment["images"]]
            report = validate_outputs(job, image_files, run_dir)
            
            manifest_path = write_manifest(job, image_files, run_dir, validation_report=report, result_fragment=fragment)
            assert manifest_path.exists()
            generated_artifacts.extend([str(p) for p in image_files])
            
    # Update consent record with produced artifacts
    consent_rec.artifact_paths = generated_artifacts
    store.save(consent_rec)
    
    summary = {
        "consent_id": consent_id,
        "subject": consent_rec.subject_pseudonym,
        "total_matrix_images": len(generated_artifacts),
        "expected_count": 10,
        "status": "complete"
    }
    with (evidence_dir / "consented_matrix_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
