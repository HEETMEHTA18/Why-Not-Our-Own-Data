from typing import List, Tuple, Set
from .models import InstructionExample


class DatasetCleaner:
    def find_duplicates(self, examples: List[InstructionExample]) -> List[Tuple[str, str]]:
        seen: Set[str] = set()
        duplicates: List[Tuple[str, str]] = []
        for ex in examples:
            key = f"{ex.instruction.strip().lower()}||{ex.output.strip().lower()}"
            if key in seen:
                duplicates.append((ex.id, "exact_duplicate"))
            seen.add(key)
        return duplicates

    def find_near_duplicates(self, examples: List[InstructionExample], threshold: float = 0.95) -> List[Tuple[str, str, float]]:
        if len(examples) < 2:
            return []
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            model = SentenceTransformer("all-MiniLM-L6-v2")
            texts = [f"{e.instruction} {e.output}" for e in examples]
            embs = model.encode(texts)
            sim = cosine_similarity(embs)

            duplicates = []
            for i in range(len(examples)):
                for j in range(i + 1, len(examples)):
                    if sim[i][j] > threshold:
                        duplicates.append((examples[i].id, examples[j].id, float(sim[i][j])))
            return duplicates
        except ImportError:
            return []

    def remove_spam(self, examples: List[InstructionExample]) -> List[InstructionExample]:
        spam_keywords = ["as an ai", "i cannot", "i'm sorry", "i am sorry",
                         "i don't have", "not able to", "cannot assist"]
        cleaned = []
        for ex in examples:
            text = f"{ex.instruction} {ex.output}".lower()
            if any(kw in text for kw in spam_keywords):
                continue
            if len(ex.output.strip()) < 5:
                continue
            cleaned.append(ex)
        return cleaned

    def find_contradictions(self, examples: List[InstructionExample]) -> List[Tuple[str, str, str]]:
        same_instruction: dict = {}
        contradictions = []
        for ex in examples:
            key = ex.instruction.strip().lower()
            if key in same_instruction:
                prev = same_instruction[key]
                if prev.output.strip().lower() != ex.output.strip().lower():
                    contradictions.append((prev.id, ex.id, f"Same instruction, different outputs"))
            else:
                same_instruction[key] = ex
        return contradictions

    def clean(self, examples: List[InstructionExample]) -> Tuple[List[InstructionExample], dict]:
        report = {
            "total_input": len(examples),
            "duplicates_removed": 0,
            "spam_removed": 0,
            "contradictions_found": 0,
        }

        duplicates = self.find_duplicates(examples)
        duplicate_ids = {d[0] for d in duplicates}
        report["duplicates_removed"] = len(duplicate_ids)

        cleaned = [e for e in examples if e.id not in duplicate_ids]
        cleaned = self.remove_spam(cleaned)
        report["spam_removed"] = len(examples) - len(cleaned) - report["duplicates_removed"]

        contradictions = self.find_contradictions(cleaned)
        report["contradictions_found"] = len(contradictions)

        return cleaned, report
