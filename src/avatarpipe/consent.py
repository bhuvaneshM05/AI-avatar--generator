"""consent.py -- Consent record management (Exceptional tier).

Provides:
  - ConsentRecord: Pydantic schema for a consent record
  - ConsentStore: File-based store for consent records (JSON per record)
  - check_consent(consent_id): validates a consent record exists and is active
  - revoke_consent(consent_id): marks a consent record as revoked
  - delete_artifacts(consent_id): erases generated images tied to a consent record

Design: consent records are stored as individual JSON files in
consent_store/<consent_id>.json. This makes erasure (GDPR right to be
forgotten) a simple file deletion + manifest update -- no database needed.

The pipeline MUST call check_consent() before any job that has reference_images.
This is enforced at the CLI level and tested in tests/unit/test_consent.py.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class ConsentRecord(BaseModel):
    """A consent record for one individual whose reference images are used.

    Fields are minimal by design -- we record only what is necessary for
    valid consent tracking. No biometric data is stored here.
    """
    consent_id: str = Field(..., description="Unique consent record identifier")
    subject_pseudonym: str = Field(
        ...,
        description=(
            "A pseudonym or code for the subject. NOT their real name -- "
            "real name storage is out of scope for this pipeline."
        ),
    )
    consented_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    revoked_at: Optional[datetime] = Field(None, description="Set when consent is revoked")
    artifact_paths: list[str] = Field(
        default_factory=list,
        description="Paths to generated images produced under this consent",
    )
    notes: str = Field("", description="Optional notes (e.g. scope of consent)")

    @property
    def is_active(self) -> bool:
        """True if consent has been given and not revoked."""
        return self.revoked_at is None


@dataclass
class ConsentCheckResult:
    """Result of a consent validity check."""
    valid: bool
    reason: str
    record: Optional[ConsentRecord] = None


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class ConsentStore:
    """File-based consent record store.

    Each record is stored as <store_dir>/<consent_id>.json.
    Thread safety: not guaranteed for concurrent writes (out of scope for
    a single-user pipeline). For production, replace with a proper DB.
    """

    def __init__(self, store_dir: Path = Path("consent_store")):
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, consent_id: str) -> Path:
        return self._dir / f"{consent_id}.json"

    def save(self, record: ConsentRecord) -> Path:
        """Persist a consent record to disk."""
        path = self._path(record.consent_id)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(record.model_dump(mode="json"), fh, indent=2, default=str)
        return path

    def load(self, consent_id: str) -> Optional[ConsentRecord]:
        """Load a consent record by ID. Returns None if not found."""
        path = self._path(consent_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return ConsentRecord(**data)

    def revoke(self, consent_id: str) -> ConsentCheckResult:
        """Revoke consent by setting revoked_at timestamp.

        Returns:
            ConsentCheckResult indicating success or failure.
        """
        record = self.load(consent_id)
        if record is None:
            return ConsentCheckResult(valid=False, reason=f"Consent record {consent_id} not found")
        if record.revoked_at is not None:
            return ConsentCheckResult(
                valid=False,
                reason=f"Consent {consent_id} was already revoked at {record.revoked_at}",
                record=record,
            )
        record.revoked_at = datetime.now(tz=timezone.utc)
        self.save(record)
        return ConsentCheckResult(valid=True, reason="Consent revoked successfully", record=record)

    def delete_artifacts(self, consent_id: str) -> dict:
        """Delete all generated images associated with a consent record.

        This implements the "right to erasure" -- after calling this,
        generated images tied to this subject are gone from disk.

        Args:
            consent_id: The consent record ID.

        Returns:
            Dict with: consent_id, deleted_paths, errors.
        """
        record = self.load(consent_id)
        if record is None:
            return {"consent_id": consent_id, "error": "Record not found", "deleted_paths": []}

        deleted = []
        errors = []
        for path_str in record.artifact_paths:
            path = Path(path_str)
            try:
                if path.exists():
                    path.unlink()
                    deleted.append(path_str)
            except Exception as exc:
                errors.append({"path": path_str, "error": str(exc)})

        # Clear artifact_paths after deletion
        record.artifact_paths = []
        self.save(record)

        return {"consent_id": consent_id, "deleted_paths": deleted, "errors": errors}


# ---------------------------------------------------------------------------
# Module-level default store and public API
# ---------------------------------------------------------------------------

_default_store = ConsentStore()


def check_consent(consent_id: str, store: Optional[ConsentStore] = None) -> ConsentCheckResult:
    """Check that a consent record exists and is currently active.

    This is the primary gate called before any reference-image job.

    Args:
        consent_id: The consent record ID to validate.
        store:      Optional custom store (uses default store if None).

    Returns:
        ConsentCheckResult with valid=True if consent is active.
    """
    s = store or _default_store
    record = s.load(consent_id)

    if record is None:
        return ConsentCheckResult(
            valid=False,
            reason=f"Consent record '{consent_id}' not found. "
                   "Create a consent record before running reference-image jobs.",
        )

    if not record.is_active:
        return ConsentCheckResult(
            valid=False,
            reason=f"Consent '{consent_id}' has been revoked at {record.revoked_at}. "
                   "Reference-image generation is not permitted.",
            record=record,
        )

    return ConsentCheckResult(
        valid=True,
        reason="Consent is active",
        record=record,
    )
