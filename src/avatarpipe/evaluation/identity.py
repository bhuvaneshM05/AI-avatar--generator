"""identity.py -- Embedding-based identity consistency scoring (Exceptional tier).

Measures whether avatars generated from the same spec (with different poses
or seeds) maintain consistent identity characteristics, using face embeddings
from a model entirely separate from the generator.

Model used: InsightFace buffalo_l (ArcFace backbone, MIT license).
This is deliberately a DIFFERENT model family from the SDXL generator --
using the same model family would create circular validation.

Note: This module requires insightface to be installed:
  pip install insightface onnxruntime
It will gracefully degrade if not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def compute_identity_similarity(
    image_a: Path,
    image_b: Path,
    model_name: str = "buffalo_l",
) -> Optional[float]:
    """Compute face embedding cosine similarity between two images.

    Args:
        image_a, image_b: Paths to two avatar images to compare.
        model_name: InsightFace model pack name.

    Returns:
        Cosine similarity in [-1, 1]. Higher = more similar identity.
        Returns None if no face is detected in either image.

    Raises:
        ImportError: If insightface or onnxruntime is not installed.
    """
    try:
        import insightface
        import numpy as np
        from insightface.app import FaceAnalysis
    except ImportError as exc:
        raise ImportError(
            "insightface and onnxruntime required for identity scoring. "
            "Install with: pip install insightface onnxruntime"
        ) from exc

    import cv2

    app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    def get_embedding(img_path: Path) -> Optional[Any]:
        img = cv2.imread(str(img_path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {img_path}")
        faces = app.get(img)
        if not faces:
            return None
        # Use the largest detected face
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return largest.embedding

    emb_a = get_embedding(image_a)
    emb_b = get_embedding(image_b)

    if emb_a is None or emb_b is None:
        return None

    # Cosine similarity
    import numpy as np
    cos_sim = float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))
    return cos_sim


def compute_identity_consistency(image_paths: list[Path], **kwargs) -> dict[str, Any]:
    """Compute pairwise identity similarity across a set of images.

    Args:
        image_paths: List of image paths (typically same identity, different poses).
        **kwargs:    Forwarded to compute_identity_similarity.

    Returns:
        Dict with:
          pairwise_scores: list of {image_a, image_b, similarity}
          mean_similarity: float
          min_similarity: float
    """
    if len(image_paths) < 2:
        return {"error": "Need at least 2 images for identity consistency", "mean_similarity": None}

    results = []
    for i, a in enumerate(image_paths):
        for b in image_paths[i + 1:]:
            try:
                sim = compute_identity_similarity(a, b, **kwargs)
                results.append({"image_a": str(a), "image_b": str(b), "similarity": sim})
            except Exception as exc:
                results.append({"image_a": str(a), "image_b": str(b), "similarity": None, "error": str(exc)})

    valid_scores = [r["similarity"] for r in results if r.get("similarity") is not None]

    return {
        "pairwise_scores": results,
        "mean_similarity": round(sum(valid_scores) / len(valid_scores), 4) if valid_scores else None,
        "min_similarity": round(min(valid_scores), 4) if valid_scores else None,
        "max_similarity": round(max(valid_scores), 4) if valid_scores else None,
        "pairs_evaluated": len(results),
        "pairs_with_faces": len(valid_scores),
    }
