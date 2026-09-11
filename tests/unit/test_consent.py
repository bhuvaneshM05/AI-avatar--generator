"""Unit tests for avatarpipe.consent -- consent record management.

Tests cover: record creation, check_consent, refusal without consent, revocation.
All tests use a temporary store directory (no persistent side effects).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from avatarpipe.consent import ConsentRecord, ConsentStore, check_consent


@pytest.fixture()
def store(tmp_path: Path) -> ConsentStore:
    return ConsentStore(store_dir=tmp_path / "consent_store")


class TestConsentStore:
    def test_save_and_load_roundtrip(self, store):
        record = ConsentRecord(consent_id="c-001", subject_pseudonym="SUBJECT_A")
        store.save(record)
        loaded = store.load("c-001")
        assert loaded is not None
        assert loaded.consent_id == "c-001"
        assert loaded.is_active

    def test_load_nonexistent_returns_none(self, store):
        assert store.load("does-not-exist") is None


class TestCheckConsent:
    def test_valid_consent_passes(self, store):
        record = ConsentRecord(consent_id="c-002", subject_pseudonym="SUBJECT_B")
        store.save(record)
        result = check_consent("c-002", store=store)
        assert result.valid is True

    def test_missing_consent_refused(self, store):
        """Core Exceptional requirement: refusal when consent absent."""
        result = check_consent("nonexistent-id", store=store)
        assert result.valid is False
        assert "not found" in result.reason.lower()

    def test_revoked_consent_refused(self, store):
        record = ConsentRecord(consent_id="c-003", subject_pseudonym="SUBJECT_C")
        store.save(record)
        store.revoke("c-003")
        result = check_consent("c-003", store=store)
        assert result.valid is False
        assert "revoked" in result.reason.lower()


class TestDeleteArtifacts:
    def test_delete_artifacts_removes_files(self, store, tmp_path):
        img = tmp_path / "face_output.png"
        img.write_bytes(b"fake image data")
        record = ConsentRecord(
            consent_id="c-004",
            subject_pseudonym="SUBJECT_D",
            artifact_paths=[str(img)],
        )
        store.save(record)
        result = store.delete_artifacts("c-004")
        assert str(img) in result["deleted_paths"]
        assert not img.exists()

    def test_delete_clears_artifact_paths_from_record(self, store, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"x")
        record = ConsentRecord(consent_id="c-005", subject_pseudonym="X", artifact_paths=[str(img)])
        store.save(record)
        store.delete_artifacts("c-005")
        reloaded = store.load("c-005")
        assert reloaded.artifact_paths == []
