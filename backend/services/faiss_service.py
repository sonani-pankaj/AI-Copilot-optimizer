# See: specs/backend/query-endpoint.md, upsert-endpoint.md — FAISS Vector Index
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_INDEX_PATH = Path(os.environ.get("FAISS_INDEX_PATH", "./data/faiss.index"))
_MODEL_NAME = "all-MiniLM-L6-v2"
_DIM = 384  # all-MiniLM-L6-v2 embedding dimension


class FaissService:
    """Thread-safe FAISS index wrapper with disk persistence.

    Uses IndexFlatIP (inner product) on L2-normalized vectors,
    which is equivalent to cosine similarity.
    """

    def __init__(self) -> None:
        self._model: Optional[SentenceTransformer] = None
        self._index: Optional[faiss.IndexIDMap] = None
        # Maps FAISS integer ID → Postgres row UUID string
        self._id_map: dict[int, str] = {}
        self._next_id: int = 0
        self._lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load model and FAISS index at startup."""
        logger.info("Loading SentenceTransformer model: %s", _MODEL_NAME)
        self._model = SentenceTransformer(_MODEL_NAME)

        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        meta_path = _INDEX_PATH.with_suffix(".meta.npy")

        if _INDEX_PATH.exists() and meta_path.exists():
            logger.info("Loading FAISS index from %s", _INDEX_PATH)
            inner = faiss.read_index(str(_INDEX_PATH))
            self._index = inner
            meta = np.load(str(meta_path), allow_pickle=True).item()
            self._id_map = meta.get("id_map", {})
            self._next_id = meta.get("next_id", 0)
            logger.info("FAISS index loaded: %d vectors", self._index.ntotal)
        else:
            logger.info("No existing FAISS index — creating fresh index")
            inner = faiss.IndexFlatIP(_DIM)
            self._index = faiss.IndexIDMap(inner)

    def save(self) -> None:
        """Persist FAISS index and ID map to disk."""
        if self._index is None:
            return
        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(_INDEX_PATH))
        meta_path = _INDEX_PATH.with_suffix(".meta.npy")
        np.save(str(meta_path), {"id_map": self._id_map, "next_id": self._next_id})
        logger.info("FAISS index persisted: %d vectors", self._index.ntotal)

    # ── Embedding ──────────────────────────────────────────────────────────

    def embed(self, text: str) -> np.ndarray:
        """Return a unit-normalized embedding vector for *text*."""
        vec = self._model.encode([text], normalize_embeddings=True)
        return vec.astype(np.float32)

    # ── Search ─────────────────────────────────────────────────────────────

    async def search(self, text: str) -> Tuple[Optional[str], float]:
        """Search index for *text*.  Returns (postgres_uuid | None, similarity)."""
        async with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return None, 0.0
            vec = self.embed(text)
            distances, ids = self._index.search(vec, k=1)
            similarity: float = float(distances[0][0])
            faiss_id: int = int(ids[0][0])
            if faiss_id == -1:
                return None, 0.0
            pg_id = self._id_map.get(faiss_id)
            return pg_id, similarity

    # ── Upsert ─────────────────────────────────────────────────────────────

    async def add(self, text: str, postgres_uuid: str) -> None:
        """Embed *text* and add to the FAISS index, then persist to disk."""
        async with self._lock:
            vec = self.embed(text)
            fid = np.array([self._next_id], dtype=np.int64)
            self._index.add_with_ids(vec, fid)
            self._id_map[self._next_id] = postgres_uuid
            self._next_id += 1
            self.save()


# Module-level singleton — loaded once at app startup
faiss_service = FaissService()
