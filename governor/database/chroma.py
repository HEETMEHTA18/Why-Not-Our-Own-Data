from pathlib import Path
from typing import Optional, List
import chromadb
from chromadb.config import Settings as ChromaSettings
from ..config import settings


class ChromaStore:
    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.chroma_path
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collections: dict = {}

    def get_or_create_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    def add(self, collection: str, ids: List[str], embeddings: List[List[float]],
            metadatas: List[dict], documents: List[str]):
        col = self.get_or_create_collection(collection)
        col.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(self, collection: str, query_embedding: List[float], n: int = 5):
        col = self.get_or_create_collection(collection)
        return col.query(query_embeddings=[query_embedding], n_results=n)

    def delete_collection(self, name: str):
        self.client.delete_collection(name)
        self._collections.pop(name, None)

    def count(self, collection: str) -> int:
        col = self.get_or_create_collection(collection)
        return col.count()
