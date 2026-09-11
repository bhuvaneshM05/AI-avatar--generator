"""adherence.py -- Prompt/spec adherence scoring using CLIP.

Measures how well a generated image matches the requested attributes by
computing the cosine similarity between the resolved text prompt and the
image embedding in CLIP's shared latent space.

Score interpretation:
  >= 0.30  Good adherence (typical for well-described prompts)
  0.20-0.30 Moderate adherence
  < 0.20   Poor adherence (image may not match the prompt)

Design decision: using open_clip (MIT license) with the laion2b ViT-B/32
checkpoint -- the same embedding space used by many open diffusion models
during training, making it a natural adherence oracle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def score_adherence(
    image_path: Path,
    prompt: str,
    model_name: str = "ViT-B-32",
    pretrained: str = "laion2b_s34b_b79k",
    device: str = "cpu",
) -> float:
    """Compute CLIP cosine similarity between prompt and image.

    Args:
        image_path: Path to the generated image file.
        prompt:     The positive prompt string used for generation.
        model_name: CLIP model variant (from open_clip model registry).
        pretrained: Pretrained weights name.
        device:     Torch device ('cpu' for local testing).

    Returns:
        Cosine similarity score in range [-1, 1], typically [0, 1] for
        prompt-image pairs. Higher = better adherence.

    Raises:
        ImportError: If open_clip_torch or torch is not installed.
        FileNotFoundError: If image_path does not exist.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        import open_clip
        import torch
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "open_clip_torch and torch are required for adherence scoring. "
            "Install with: pip install open-clip-torch torch"
        ) from exc

    # Load model and preprocessing transforms
    # Note: model weights are downloaded on first call (~340MB for ViT-B/32)
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name, pretrained=pretrained, device=device
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    model.eval()

    # Preprocess image and tokenize prompt
    img = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
    tokens = tokenizer([prompt]).to(device)

    with torch.no_grad():
        image_features = model.encode_image(img)
        text_features = model.encode_text(tokens)
        # L2-normalise before dot product (= cosine similarity)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (image_features @ text_features.T).item()

    return float(similarity)


def score_batch(
    image_prompt_pairs: list[tuple[Path, str]],
    **kwargs,
) -> list[dict]:
    """Score adherence for a batch of (image, prompt) pairs.

    Args:
        image_prompt_pairs: List of (image_path, prompt) tuples.
        **kwargs:           Forwarded to score_adherence().

    Returns:
        List of dicts with keys: image_path, prompt, score.
    """
    results = []
    for img_path, prompt in image_prompt_pairs:
        try:
            score = score_adherence(img_path, prompt, **kwargs)
            results.append({"image_path": str(img_path), "prompt": prompt, "score": score, "error": None})
        except Exception as exc:
            results.append({"image_path": str(img_path), "prompt": prompt, "score": None, "error": str(exc)})
    return results
