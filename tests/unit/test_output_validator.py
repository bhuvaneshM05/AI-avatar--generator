"""Unit tests for avatarpipe.output_validator."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from avatarpipe.output_validator import validate_outputs


@pytest.fixture()
def job_bundle() -> dict:
    return {
        "job_id": "test-job-001",
        "spec": {"aspect_ratio": "1:1"},
        "seed": 42,
        "model": {"name": "test"},
    }


class TestOutputValidator:
    def test_valid_png_passes(self, tmp_path, job_bundle):
        img = Image.new("RGB", (1024, 1024), color=(100, 150, 200))
        img_path = tmp_path / "output.png"
        img.save(img_path)
        report = validate_outputs(job_bundle, [img_path], tmp_path)
        assert report.image_results[0].readable

    def test_corrupt_file_fails_readable(self, tmp_path, job_bundle):
        corrupt = tmp_path / "corrupt.png"
        corrupt.write_bytes(b"not a valid image \x00\x01\x02\x03 garbage data")
        report = validate_outputs(job_bundle, [corrupt], tmp_path)
        assert not report.image_results[0].readable
        assert report.failed_images == 1
        assert not report.all_passed

    def test_report_has_correct_counts(self, tmp_path, job_bundle):
        # Use a gradient-like image (non-uniform pixels) so non-blank check passes
        import numpy as np
        from PIL import Image as PILImage
        valid = tmp_path / "v.png"
        arr = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
        PILImage.fromarray(arr).save(valid)
        corrupt = tmp_path / "c.png"
        corrupt.write_bytes(b"garbage")
        report = validate_outputs(job_bundle, [valid, corrupt], tmp_path)
        assert report.total_images == 2
        assert report.passed_images == 1
        assert report.failed_images == 1

    def test_report_to_dict_is_serialisable(self, tmp_path, job_bundle):
        import json
        valid = tmp_path / "v.png"
        Image.new("RGB", (64, 64), (200, 100, 50)).save(valid)
        report = validate_outputs(job_bundle, [valid], tmp_path)
        d = report.to_dict()
        assert json.dumps(d)  # should not raise

    def test_fragment_present_true_when_file_exists(self, tmp_path, job_bundle):
        import json
        frag = tmp_path / "result_fragment.json"
        frag.write_text(json.dumps({"image_hashes": {}}))
        valid = tmp_path / "v.png"
        Image.new("RGB", (64, 64), (100, 100, 100)).save(valid)
        report = validate_outputs(job_bundle, [valid], tmp_path)
        assert report.fragment_present

    def test_fragment_present_false_when_missing(self, tmp_path, job_bundle):
        valid = tmp_path / "v.png"
        Image.new("RGB", (64, 64), (100, 100, 100)).save(valid)
        report = validate_outputs(job_bundle, [valid], tmp_path)
        assert not report.fragment_present
