"""
ai_engine/embeddings/database_builder.py
=========================================

Offline pipeline: raw dataset images -> FAISS index + id mapping.

Run once before starting the API:
    python scripts/02_build_faiss_index.py

Flow:
    data/raw_images/*.jpg
        -> metadata validation against data/metadata.json
        -> FashionCLIPEncoder.encode()       (512-d L2-normalized vector)
        -> faiss.IndexFlatIP                 (cosine similarity via dot product)
        -> data/embeddings.index             (FAISS binary)
        -> data/index_to_image_id.json       (faiss_id -> image filename)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from tqdm import tqdm

from ai_engine.embeddings.encoder import EMBEDDING_DIM, get_encoder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

DEFAULT_IMAGES_DIR = Path("data/raw_images")
DEFAULT_INDEX_PATH = Path("data/embeddings.index")
DEFAULT_MAPPING_PATH = Path("data/index_to_image_id.json")
DEFAULT_METADATA_SOURCE_PATH = Path("data/metadata.json")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FAISSIndexBuilder:
    """Builds a FAISS IndexFlatIP from catalog images with strict metadata validation."""

    def __init__(
        self,
        index_path: Path = DEFAULT_INDEX_PATH,
        mapping_path: Path = DEFAULT_MAPPING_PATH,
        metadata_source_path: Path = DEFAULT_METADATA_SOURCE_PATH,
    ) -> None:
        self.index_path = Path(index_path)
        self.mapping_path = Path(mapping_path)
        self.metadata_source_path = Path(metadata_source_path)
        self._encoder = get_encoder()

    def build(self, images_dir: Path = DEFAULT_IMAGES_DIR) -> None:
        """Full build pipeline with strict validation rules."""
        import faiss

        images_dir = Path(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        image_paths = self._collect_images(images_dir)
        if not image_paths:
            raise FileNotFoundError(
                f"No images found in {images_dir}. Add images before building the index."
            )

        metadata = self._load_metadata()
        logger.info("Building FAISS index for %d candidate images...", len(image_paths))

        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        mapping: dict[str, str] = {}

        for path in tqdm(image_paths, desc="Indexing images", unit="image"):
            metadata_key = path.stem
            if metadata_key not in metadata:
                logger.warning(
                    "Skipping %s: missing metadata key '%s'", path.name, metadata_key
                )
                continue

            try:
                vector = self._embed_image(path)
                faiss_id = str(index.ntotal)
                index.add(np.expand_dims(vector, axis=0))
                mapping[faiss_id] = path.name
            except Exception as exc:
                logger.warning("Skipping %s: %s", path.name, exc)

        if index.ntotal == 0:
            raise ValueError(
                "No valid images were indexed. Ensure images exist and metadata entries match filenames."
            )

        self._save(index, mapping)
        logger.info("Index built successfully: %d vectors", index.ntotal)

    def _collect_images(self, images_dir: Path) -> list[Path]:
        """Return sorted list of supported image paths."""
        return sorted(
            p
            for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def _load_metadata(self) -> dict:
        """Load metadata catalog used for validation."""
        if not self.metadata_source_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found at {self.metadata_source_path}. "
                "Create data/metadata.json before building the index."
            )
        with open(self.metadata_source_path, "r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        if not isinstance(data, dict):
            raise ValueError(
                "data/metadata.json must be a JSON object keyed by item IDs."
            )
        return data

    def _embed_image(self, path: Path) -> np.ndarray:
        """Read image file -> L2-normalized 512-d vector."""
        with open(path, "rb") as file_obj:
            return self._encoder.encode(file_obj.read())

    def _save(self, index, mapping: dict[str, str]) -> None:
        """Persist FAISS index and id mapping to disk."""
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(self.index_path))
        with open(self.mapping_path, "w", encoding="utf-8") as file_obj:
            json.dump(mapping, file_obj, indent=2)

        logger.info("Saved index   -> %s", self.index_path)
        logger.info("Saved mapping -> %s", self.mapping_path)


def build_index(
    images_dir: Path = DEFAULT_IMAGES_DIR,
    index_path: Path = DEFAULT_INDEX_PATH,
    mapping_path: Path = DEFAULT_MAPPING_PATH,
    metadata_source_path: Path = DEFAULT_METADATA_SOURCE_PATH,
) -> None:
    """Convenience entrypoint for scripts."""
    FAISSIndexBuilder(
        index_path=index_path,
        mapping_path=mapping_path,
        metadata_source_path=metadata_source_path,
    ).build(images_dir=images_dir)
