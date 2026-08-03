import numpy as np
import pickle
from pathlib import Path
from typing import Optional, List, Tuple
import faiss
from ..config import settings


class FAISSStore:
    def __init__(self, index_path: Optional[Path] = None, dim: int = 384):
        self.index_path = index_path or settings.faiss_index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.id_map: List[str] = []
        self._load()

    def _load(self):
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            map_path = self.index_path.with_suffix(".map")
            if map_path.exists():
                with open(map_path, "rb") as f:
                    self.id_map = pickle.load(f)

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        map_path = self.index_path.with_suffix(".map")
        with open(map_path, "wb") as f:
            pickle.dump(self.id_map, f)

    def add(self, ids: List[str], embeddings: List[List[float]]):
        emb = np.array(embeddings, dtype=np.float32)
        if len(emb.shape) == 1:
            emb = emb.reshape(1, -1)
        self.index.add(emb)
        self.id_map.extend(ids)
        self._save()

    def search(self, query_emb: List[float], k: int = 5) -> Tuple[List[str], List[float]]:
        q = np.array([query_emb], dtype=np.float32)
        distances, indices = self.index.search(q, k)
        results = []
        scores = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.id_map):
                results.append(self.id_map[idx])
                scores.append(float(distances[0][i]))
        return results, scores

    def size(self) -> int:
        return self.index.ntotal

    def reset(self):
        self.index = faiss.IndexFlatL2(self.dim)
        self.id_map = []
        self._save()
