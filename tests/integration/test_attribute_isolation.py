"""Integration tests: Controlled Single-Attribute Changes.

Implements Phase 6 item 2:
Four controlled single-attribute changes holding all other fields constant:
1. Base spec: Young adult feminine, Fitzpatrick III, wavy brown hair, blazer, office, seed 2000
2. Swap 1: Attire changed (blazer -> casual knit sweater)
3. Swap 2: Hair changed (wavy brown -> short platinum buzzcut)
4. Swap 3: Background changed (office -> serene sunset lakeside)
5. Swap 4: Age band changed (young_adult -> senior)

Saves job bundles, output validations, manifests, and comparative analysis
into evidence/test_matrix/attribute_isolation/.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from avatarpipe.spec import AvatarSpec, AgeBand, Presentation, AspectRatio, HairSpec
from avatarpipe.job_builder import build_job
from avatarpipe.inference_adapter import LocalCPUStubAdapter
from avatarpipe.output_validator import validate_outputs
from avatarpipe.manifest import write_manifest, load_manifest

BASE_SPEC_DICT = {
    "age_band": AgeBand.young_adult,
    "presentation": Presentation.feminine,
    "skin_tone": "Fitzpatrick III (medium olive)",
    "hair": HairSpec(style="shoulder-length wavy", color="chestnut brown"),
    "attire": "tailored charcoal blazer",
    "background": "minimalist studio office with clean backdrop",
    "pose": "neutral front-facing portrait",
    "aspect_ratio": AspectRatio.one_to_one,
    "seed": 2000,
}

SWAPS = [
    ("base", {}),
    ("swap_attire", {"attire": "relaxed oversized cream cable-knit sweater"}),
    ("swap_hair", {"hair": HairSpec(style="short cropped buzzcut", color="platinum blonde")}),
    ("swap_background", {"background": "tranquil lakeside at twilight with glowing lanterns"}),
    ("swap_age_band", {"age_band": AgeBand.senior}),
]

def test_controlled_attribute_isolation(tmp_path):
    config_dir = Path("config")
    evidence_dir = Path("evidence/test_matrix/attribute_isolation")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    adapter = LocalCPUStubAdapter(width=256, height=256)
    manifests = {}
    
    for case_name, delta in SWAPS:
        spec_data = BASE_SPEC_DICT.copy()
        spec_data.update(delta)
        spec = AvatarSpec(**spec_data)
        
        job = build_job(spec, config_dir)
        case_dir = evidence_dir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        
        job_file = case_dir / "job.json"
        with job_file.open("w", encoding="utf-8") as f:
            json.dump(job, f, indent=2, default=str)
            
        fragment = adapter.run(job, case_dir)
        image_files = [Path(p) for p in fragment["images"]]
        report = validate_outputs(job, image_files, case_dir)
        
        manifest_path = write_manifest(job, image_files, case_dir, validation_report=report, result_fragment=fragment)
        manifest = load_manifest(manifest_path)
        manifests[case_name] = manifest
        
        # Verify seed isolation (seed remains exactly 2000 across all swaps)
        assert manifest["seed"] == 2000
        
    # Verify differential isolation between base and swaps
    base_prompt = manifests["base"]["prompt"]
    
    # 1. Attire swap changed attire but not hair/age/background
    attire_prompt = manifests["swap_attire"]["prompt"]
    assert "cable-knit sweater" in attire_prompt
    assert "charcoal blazer" not in attire_prompt
    assert "chestnut brown" in attire_prompt
    
    # 2. Hair swap changed hair but not attire
    hair_prompt = manifests["swap_hair"]["prompt"]
    assert "platinum blonde" in hair_prompt
    assert "charcoal blazer" in hair_prompt
    
    # 3. Background swap changed background
    bg_prompt = manifests["swap_background"]["prompt"]
    assert "lakeside" in bg_prompt
    assert "charcoal blazer" in bg_prompt
    
    # 4. Age band swap changed age
    age_prompt = manifests["swap_age_band"]["prompt"]
    assert "senior" in age_prompt
    assert "young adult" not in age_prompt
    assert "charcoal blazer" in age_prompt
    
    summary = {
        "base_spec": BASE_SPEC_DICT["seed"],
        "cases_tested": [k for k, _ in SWAPS],
        "isolation_verified": True
    }
    with (evidence_dir / "attribute_isolation_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
