"""
scripts/(C)_build_faiss_index.py
==================================
Rebuilds the local FAISS index from scratch off every image currently in
data/raw_images/. Needed because:
  - scripts/build_database.py is broken (imports a database_builder.py
    that doesn't exist in this repo)
  - FAISS IndexFlatIP has no in-place delete/update, so this is how
    removed brands (activ) actually drop out of retrieval and newly
    ingested brands actually become searchable

Encodes with the existing FashionCLIPEncoder singleton
(ai_engine/embeddings/encoder.py) -- 512-dim, L2-normalized, unchanged.
Writes:
  - data/embeddings.index          (faiss.IndexFlatIP)
  - data/index_to_image_id.json    (row index -> filename, same shape
                                     as the file it replaces)

Backs up both existing files before overwriting (data/ is git-ignored --
no version-control safety net).

Usage:
  python scripts/(C)_build_faiss_index.py
"""

import json
import shutil
import sys
import time
from pathlib import Path

import faiss
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.embeddings.encoder import get_encoder  # noqa: E402

RAW_IMAGES_DIR = Path("data/raw_images")
INDEX_PATH = Path("data/embeddings.index")
MAPPING_PATH = Path("data/index_to_image_id.json")
EMBEDDING_DIM = 512


def main():
    for path in (INDEX_PATH, MAPPING_PATH):
        if path.exists():
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup)
            print(f"Backed up {path} -> {backup}")

    filenames = sorted(p.name for p in RAW_IMAGES_DIR.iterdir() if p.is_file())
    print(f"Encoding {len(filenames)} images from {RAW_IMAGES_DIR}...")

    encoder = get_encoder()

    vectors = np.zeros((len(filenames), EMBEDDING_DIM), dtype=np.float32)
    id_to_filename = {}
    failed = []
    kept = 0
    start = time.time()

    for i, filename in enumerate(filenames):
        filepath = RAW_IMAGES_DIR / filename
        try:
            image_bytes = filepath.read_bytes()
            vec = encoder.encode(image_bytes)
            vectors[kept] = vec
            id_to_filename[str(kept)] = filename
            kept += 1
        except Exception as e:
            failed.append((filename, str(e)))

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (len(filenames) - (i + 1)) / rate if rate > 0 else float("inf")
            print(f"  [{i + 1}/{len(filenames)}] {rate:.1f} img/s | "
                  f"ETA {remaining/60:.1f} min | {len(failed)} failed so far")

    vectors = vectors[:kept]

    print(f"\nEncoded {kept} vectors ({len(failed)} failed/unreadable)")

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(vectors)
    faiss.write_index(index, str(INDEX_PATH))

    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(id_to_filename, f, indent=2)

    elapsed = time.time() - start
    print(f"\nWrote {INDEX_PATH} ({index.ntotal} vectors) and {MAPPING_PATH} in {elapsed/60:.1f} min")

    if failed:
        print(f"\n{len(failed)} images failed to encode (first 10 shown):")
        for filename, err in failed[:10]:
            print(f"  {filename}: {err}")


if __name__ == "__main__":
    main()
