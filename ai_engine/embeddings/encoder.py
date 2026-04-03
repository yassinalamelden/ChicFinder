"""
encoder.py — VGG-16 fashion embedding encoder (256-dim, L2-normalized).

Generates compact, discriminative embeddings for clothing images.
Used both during offline database indexing and online query encoding.

Implements Step 4a of the OutfitAI architecture:
  Cropped item image → VGG-16 (256-dim bottleneck, Triplet Loss) → L2-normed vector
"""

import logging
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
from PIL import Image

from chic_finder.config import settings

logger = logging.getLogger(__name__)

# Standard ImageNet normalization (VGG-16 pre-trained expectations)
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

# Input resolution for VGG-16
_INPUT_SIZE = 224


class FashionEncoder:
    """
    FashionEncoder: VGG-16 backbone with a 256-dim embedding bottleneck.

    Architecture:
      VGG-16 conv layers (frozen or fine-tuned) →
      Adaptive Average Pool →
      FC(4096) → ReLU → Dropout →
      FC(4096) → ReLU → Dropout →
      FC(256)  ← custom bottleneck (replaces original 1000-class head)

    The output 256-dim vector is L2-normalized to unit sphere,
    enabling cosine/Euclidean equivalence for FAISS similarity search.

    Referencing: OutfitAI architecture Step 4a.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = model_path or settings.ENCODER_MODEL_PATH
        self.transform = self._build_transform()
        self.encoder = self._build_model()
        self._try_load_weights()
        logger.info(
            "FashionEncoder initialized on %s (model_path=%s)",
            self.device,
            self.model_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(self, image: Image.Image) -> torch.Tensor:
        """
        Encodes a PIL Image into a 256-dim L2-normalized embedding vector.

        Args:
            image: RGB PIL Image of the clothing item.

        Returns:
            torch.Tensor of shape (256,) on CPU, L2-normalized.
        """
        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        tensor = self.transform(image).unsqueeze(0).to(self.device)  # (1, 3, 224, 224)

        with torch.no_grad():
            embedding = self.encoder(tensor)  # (1, 256)
            embedding = F.normalize(embedding, p=2, dim=1)  # L2 normalize

        return embedding.squeeze(0).cpu()  # (256,)

    def encode_batch(self, images: list) -> torch.Tensor:
        """
        Encodes a list of PIL Images into a (N, 256) tensor.

        Args:
            images: List of PIL Images.

        Returns:
            torch.Tensor of shape (N, 256), L2-normalized rows.
        """
        if not images:
            return torch.zeros((0, 256))

        tensors = [self.transform(img.convert("RGB")) for img in images]
        batch = torch.stack(tensors).to(self.device)  # (N, 3, 224, 224)

        with torch.no_grad():
            embeddings = self.encoder(batch)  # (N, 256)
            embeddings = F.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu()  # (N, 256)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_model(self) -> nn.Module:
        """
        Builds VGG-16 with the standard ImageNet head replaced by a
        256-dim bottleneck layer for fashion embedding.

        The convolutional feature extractor is kept pre-trained.
        Only the custom classifier head is used for embedding.
        """
        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)

        # Replace classifier: keep FC-4096 × 2 dropout layers, swap last FC
        # Original: Linear(4096→4096) → ReLU → Dropout →
        #           Linear(4096→4096) → ReLU → Dropout →
        #           Linear(4096→1000)
        # Ours:     same but last Linear is 4096→256
        classifier_layers = list(vgg.classifier.children())[:-1]  # drop 4096→1000
        classifier_layers.append(nn.Linear(4096, 256))
        vgg.classifier = nn.Sequential(*classifier_layers)

        return vgg.to(self.device).eval()

    def _build_transform(self) -> transforms.Compose:
        """Standard ImageNet preprocessing pipeline for VGG-16."""
        return transforms.Compose(
            [
                transforms.Resize((_INPUT_SIZE, _INPUT_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
            ]
        )

    def _try_load_weights(self):
        """
        Attempts to load fine-tuned weights from `model_path`.
        If the file doesn't exist, logs a warning and continues with
        ImageNet-pretrained weights (still useful for fashion retrieval).
        """
        path = Path(self.model_path)
        if not path.exists():
            logger.warning(
                "FashionEncoder: fine-tuned weights not found at '%s'. "
                "Using ImageNet-pretrained VGG-16 features instead.",
                self.model_path,
            )
            return

        try:
            state_dict = torch.load(path, map_location=self.device)
            self.encoder.load_state_dict(state_dict, strict=False)
            logger.info("FashionEncoder: loaded fine-tuned weights from '%s'.", path)
        except Exception as exc:
            logger.error(
                "FashionEncoder: failed to load weights from '%s': %s. "
                "Falling back to ImageNet weights.",
                path,
                exc,
            )
