from typing import Optional, List
from ..config import settings
from .models import MemoryClass


class KnowledgeBase:
    def __init__(self):
        from ..database.chroma import ChromaStore
        from ..database.faiss_store import FAISSStore
        self.chroma = ChromaStore()
        self.faiss = FAISSStore(dim=384)
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(settings.embedding_model)
        return self._encoder

    def store(self, conversation_id: str, content: str, classification: MemoryClass):
        emb = self._get_encoder().encode(content).tolist()
        collection = f"memory_{classification.value}"
        self.chroma.add(
            collection=collection,
            ids=[conversation_id],
            embeddings=[emb],
            metadatas=[{"classification": classification.value}],
            documents=[content],
        )
        self.faiss.add([conversation_id], [emb])

    def search(self, query: str, k: int = 5) -> List[dict]:
        emb = self._get_encoder().encode(query).tolist()
        ids, scores = self.faiss.search(emb, k=k)
        chroma_results = self.chroma.query("memory_training_data", emb, n=k)
        results = []
        for i, cid in enumerate(ids):
            results.append({
                "conversation_id": cid,
                "score": scores[i],
                "source": "faiss",
            })
        if chroma_results and chroma_results["ids"]:
            for i, cid in enumerate(chroma_results["ids"][0]):
                results.append({
                    "conversation_id": cid,
                    "score": chroma_results["distances"][0][i] if chroma_results["distances"] else 0,
                    "document": chroma_results["documents"][0][i] if chroma_results["documents"] else "",
                    "source": "chroma",
                })
        return results

    def size(self) -> dict:
        return {
            "chroma_collections": {
                mc.value: self.chroma.count(f"memory_{mc.value}")
                for mc in MemoryClass
            },
            "faiss_entries": self.faiss.size(),
        }
