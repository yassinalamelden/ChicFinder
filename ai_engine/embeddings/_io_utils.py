"""
ai_engine/embeddings/_io_utils.py
==================================
Shared atomic-write helpers for the two index builders (database_builder.py,
remote_database_builder.py). A process killed mid-write (OOM, deploy
interruption) must never leave a truncated FAISS index or mapping file for
FAISSVectorStore to load — write to a temp path in the same directory, then
rename into place (atomic on both POSIX and Windows for same-filesystem
renames).
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _atomic_write_faiss_index(index, path: Path) -> None:
    import faiss

    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    faiss.write_index(index, str(tmp_path))
    os.replace(tmp_path, path)


def _atomic_write_json(data: dict, path: Path) -> None:
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, indent=2)
    os.replace(tmp_path, path)
