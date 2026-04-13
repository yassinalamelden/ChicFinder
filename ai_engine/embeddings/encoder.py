"""
ai_engine/embeddings/encoder.py
================================
Slice 2 — Yassin (branch: ai/yassin)

FashionCLIP encoder — the single source of embeddings for the entire pipeline.

Responsibilities:
  - Load patrickjohncyh/fashion-clip once at startup (singleton)
  - Decode raw image bytes → PIL RGB
  - Run FashionCLIP vision encoder → 512-d float32 vector
  - L2-normalize → ready for FAISS IndexFlatIP cosine similarity

Why FashionCLIP, why no background removal:
  - Fine-tuned on ~700k Farfetch fashion product images
  - Deep pre-trained models are unaffected by backgrounds (unlike shallow CNNs)
  - Simpler pipeline, no rembg dependency

Output contract (agreed with Moamen + Amr):
  encode(image_bytes: bytes) -> np.ndarray  shape=(512,), dtype=float32, L2-norm=1.0
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOCAL_MODEL_PATH = "models/fine_tuned_clip"
DEFAULT_MODEL_ID = "patrickjohncyh/fashion-clip"

# Use local if exists, otherwise fallback to remote
CLIP_MODEL_ID  = LOCAL_MODEL_PATH if os.path.exists(LOCAL_MODEL_PATH) else DEFAULT_MODEL_ID
EMBEDDING_DIM  = 512   # fixed — agreed contract across all slices


# ---------------------------------------------------------------------------
# Lazy imports
# ---------------------------------------------------------------------------

def _load_transformers():
    try:
        from transformers import CLIPModel, CLIPProcessor
        return CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise ImportError("Run: pip install transformers") from exc


def _load_torch():
    try:
        import torch
        return torch
    except ImportError as exc:
        raise ImportError("Run: pip install torch") from exc


# ---------------------------------------------------------------------------
# FashionCLIPEncoder  (Singleton)
# ---------------------------------------------------------------------------

class FashionCLIPEncoder:
    """
    Singleton FashionCLIP image encoder.

    Usage
    -----
    encoder = FashionCLIPEncoder.get_instance()
    vector  = encoder.encode(image_bytes)   # (512,) float32, L2-norm = 1.0

    Called by
    ---------
    - database_builder.py  : encodes every dataset image at index-build time
    - vector_store.py      : encodes the user query image at search time
    """

    _instance: Optional["FashionCLIPEncoder"] = None

    def __init__(self) -> None:
        torch = _load_torch()
        CLIPModel, CLIPProcessor = _load_transformers()

        logger.info("Loading FashionCLIP: %s", CLIP_MODEL_ID)
        self._processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)
        self._model     = CLIPModel.from_pretrained(CLIP_MODEL_ID)
        self._model.eval()

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

        logger.info(
            "FashionCLIPEncoder ready | device=%s | dim=%d",
            self._device, EMBEDDING_DIM,
        )

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "FashionCLIPEncoder":
        """Return the singleton — model loaded only on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(self, image_bytes: bytes) -> np.ndarray:
        """
        Raw image bytes → L2-normalized 512-d embedding.

        Parameters
        ----------
        image_bytes : bytes
            JPEG / PNG / WebP raw bytes of any fashion image.

        Returns
        -------
        np.ndarray
            shape=(512,), dtype=float32, ||v||_2 = 1.0
        """
        image     = self._decode(image_bytes)
        embedding = self._encode(image)
        return self._normalize(embedding)

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _decode(self, image_bytes: bytes) -> Image.Image:
        """Decode bytes → PIL RGB."""
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise ValueError(f"Cannot decode image: {exc}") from exc

    def _encode(self, image: Image.Image) -> np.ndarray:
        """PIL image → raw 512-d numpy vector via FashionCLIP."""
        import torch
        inputs  = self._processor(images=image, return_tensors="pt")
        inputs  = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            vision_outputs = self._model.vision_model(**inputs)
            features = self._model.visual_projection(vision_outputs.pooler_output)
        return features.squeeze(0).cpu().numpy().astype(np.float32)

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        """L2-normalize so dot-product == cosine similarity in FAISS."""
        norm = np.linalg.norm(vector)
        if norm < 1e-10:
            logger.warning("Near-zero norm vector — returning as-is.")
            return vector
        return vector / norm


# ---------------------------------------------------------------------------
# Convenience accessor (used everywhere in the project)
# ---------------------------------------------------------------------------

def get_encoder() -> FashionCLIPEncoder:
    """
    Module-level shortcut for the singleton encoder.

    Examples
    --------
    # database_builder.py (Amr)
    from ai_engine.embeddings.encoder import get_encoder
    vec = get_encoder().encode(open(path, "rb").read())

    # vector_store.py (Moamen)
    from ai_engine.embeddings.encoder import get_encoder
    query_vec = get_encoder().encode(image_bytes)
    """
    return FashionCLIPEncoder.get_instance()