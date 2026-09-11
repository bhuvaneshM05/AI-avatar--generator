"""inference_adapter.py -- Adapter interface for diffusion model inference.

Two concrete implementations:

  LocalCPUStubAdapter
    For unit and integration tests ONLY. Generates a tiny placeholder image
    (solid white 64x64 PNG) to prove the code path is wired up correctly,
    without touching a GPU or downloading model weights. Outputs are labelled
    provenance.route = "local-cpu-stub" and must NEVER be submitted as final
    graded avatars.

  NotebookAdapter
    Packages the job bundle for upload to the Kaggle notebook, and on return
    ingests the produced files. The actual diffusion inference happens inside
    the Kaggle notebook -- this class handles only the file I/O bookends.

Design decision: the InferenceAdapter ABC makes the local/remote split
explicit at the type level. Any future accelerator (Lightning.ai, HF ZeroGPU)
gets a new adapter class, not a branch in existing code.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class InferenceAdapter(ABC):
    """Abstract base class for all inference adapters.

    Subclasses MUST implement run() and expose a provenance_route property.
    """

    @property
    @abstractmethod
    def provenance_route(self) -> str:
        """String identifier written into the manifest provenance.route field."""
        ...

    @abstractmethod
    def run(self, job_bundle: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        """Execute inference and return a result fragment dict.

        Args:
            job_bundle: The validated job bundle dict (from load_job).
            output_dir: Directory to write output images and result_fragment.json.

        Returns:
            A result_fragment dict containing at minimum:
              - images: list of absolute str paths to generated images
              - seed: the seed used
              - model_id: the model name used
              - revision: the model revision hash used
              - provenance_route: self.provenance_route
              - generated_at: ISO 8601 UTC timestamp
              - image_hashes: {filename: sha256_hex} for each image
        """
        ...


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# LocalCPUStubAdapter
# ---------------------------------------------------------------------------

class LocalCPUStubAdapter(InferenceAdapter):
    """CPU-only stub adapter for testing pipeline plumbing without a GPU.

    Generates a tiny solid-colour placeholder image (64x64 or configurable).
    Output is clearly labelled in the manifest as non-final.

    WARNING: DO NOT use these outputs as final graded avatars. They are
    intentionally low-resolution placeholders for integration testing only.
    """

    def __init__(self, width: int = 64, height: int = 64, colour: tuple = (200, 200, 200)):
        """
        Args:
            width, height: Dimensions of the placeholder image (pixels).
            colour:        RGB fill colour. Default grey makes it visually
                           obvious that this is a stub output.
        """
        self._width = width
        self._height = height
        self._colour = colour

    @property
    def provenance_route(self) -> str:
        return "local-cpu-stub"

    def run(self, job_bundle: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        """Generate a placeholder image and write a result fragment.

        Args:
            job_bundle: Job bundle dict (prompt, seed, etc. are read for logging
                        but not actually used for generation).
            output_dir: Directory to write the placeholder PNG and fragment JSON.

        Returns:
            Result fragment dict.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate placeholder image
        img = Image.new("RGB", (self._width, self._height), color=self._colour)
        job_id = job_bundle.get("job_id", "unknown")
        img_filename = f"stub_{job_id[:8]}.png"
        img_path = output_dir / img_filename
        img.save(img_path, format="PNG")

        # Build result fragment
        fragment = {
            "images": [str(img_path)],
            "seed": job_bundle.get("seed"),
            "model_id": job_bundle.get("model", {}).get("name", "stub"),
            "revision": "stub-no-revision",
            "provenance_route": self.provenance_route,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "image_hashes": {img_filename: _sha256(img_path)},
            # Explicit non-final label -- catches any accidental submission
            "WARNING": "STUB OUTPUT -- NOT A FINAL GRADED AVATAR",
        }

        # Write fragment JSON alongside images (mirrors what the Kaggle notebook does)
        fragment_path = output_dir / "result_fragment.json"
        with fragment_path.open("w", encoding="utf-8") as fh:
            json.dump(fragment, fh, indent=2)

        return fragment


# ---------------------------------------------------------------------------
# NotebookAdapter
# ---------------------------------------------------------------------------

class NotebookAdapter(InferenceAdapter):
    """Adapter for the Kaggle notebook inference workflow.

    This adapter handles the file I/O bookends:
      - prepare(): copies the job bundle to the staging directory the notebook reads
      - run(): ingests results written by the notebook (reads result_fragment.json)

    The actual diffusion inference happens inside notebooks/inference_kaggle.ipynb
    running on Kaggle's T4 GPU -- this class never calls the model directly.
    """

    def __init__(self, staging_dir: Path = Path("jobs/staging")):
        """
        Args:
            staging_dir: Directory where job bundles are staged for upload to Kaggle.
        """
        self._staging_dir = staging_dir

    @property
    def provenance_route(self) -> str:
        return "kaggle"

    def prepare(self, job_bundle: dict[str, Any]) -> Path:
        """Copy a job bundle to the staging directory for Kaggle upload.

        Args:
            job_bundle: The job bundle dict (must contain job_id).

        Returns:
            Path to the staged JSON file.
        """
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        staged_path = self._staging_dir / f"{job_bundle['job_id']}.json"
        with staged_path.open("w", encoding="utf-8") as fh:
            json.dump(job_bundle, fh, indent=2)
        return staged_path

    def run(self, job_bundle: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        """Ingest results written by the Kaggle notebook.

        This method reads the result_fragment.json that the notebook wrote,
        validates that the referenced image files exist, and returns the
        fragment with provenance updated.

        Args:
            job_bundle: The original job bundle (used for cross-validation).
            output_dir: Directory containing the notebook's output files.

        Returns:
            The loaded result fragment dict.

        Raises:
            FileNotFoundError: If result_fragment.json or images are missing.
            ValueError:        If the fragment is malformed or seed mismatches.
        """
        fragment_path = output_dir / "result_fragment.json"
        if not fragment_path.exists():
            raise FileNotFoundError(
                f"result_fragment.json not found in {output_dir}. "
                "Did the Kaggle notebook complete successfully and write its outputs?"
            )

        with fragment_path.open("r", encoding="utf-8") as fh:
            fragment = json.load(fh)

        # Validate that the seed in the fragment matches the job bundle
        # (catches accidental runs of the wrong notebook with wrong job data)
        if fragment.get("seed") != job_bundle.get("seed"):
            raise ValueError(
                f"Seed mismatch: job bundle seed={job_bundle.get('seed')}, "
                f"fragment seed={fragment.get('seed')}. "
                "Ensure the correct job bundle was used in the Kaggle notebook."
            )

        # Validate that image files exist
        for img_path_str in fragment.get("images", []):
            img_path = Path(img_path_str)
            if not img_path.exists():
                # Try relative to output_dir (notebook may use relative paths)
                img_path = output_dir / img_path.name
            if not img_path.exists():
                raise FileNotFoundError(f"Image file not found: {img_path_str}")

        fragment["provenance_route"] = self.provenance_route
        return fragment
