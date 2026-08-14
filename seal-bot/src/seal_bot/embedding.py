from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageOps


class Hyper3ClipEmbedder:
    """Lazy Hyper3-CLIP adapter so web startup does not download model weights."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.environ.get("SEAL_HYPER3_MODEL", "hyper3-clip-v0.5")
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                import hyper_models
            except ImportError as exc:
                raise RuntimeError(
                    "Hyper3 is not installed. Run `pip install -e ../seal-bot` from cognee-demo-slack."
                ) from exc
            try:
                self._model = hyper_models.load(self.model_name)
            except Exception as exc:
                if exc.__class__.__name__ == "GatedRepoError":
                    raise RuntimeError(
                        "Hyper3 model access is gated. Request access at "
                        "https://huggingface.co/hyper3labs/hyper3-clip-v0.5, then run "
                        "`hf auth login` or set HF_TOKEN in .env."
                    ) from exc
                raise
        return self._model

    def encode_images(self, paths: Sequence[Path]) -> np.ndarray:
        if not paths:
            raise ValueError("At least one image is required")
        images: list[Image.Image] = []
        try:
            for path in paths:
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    images.append(image.copy())
            vectors = np.asarray(self._load().encode_images(images), dtype=np.float32)
        finally:
            for image in images:
                image.close()

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.ndim != 2 or vectors.shape[0] != len(paths) or vectors.shape[1] == 0:
            raise RuntimeError(f"Hyper3 returned an unexpected embedding shape: {vectors.shape}")
        if not np.isfinite(vectors).all():
            raise RuntimeError("Hyper3 returned a non-finite embedding")
        return vectors
