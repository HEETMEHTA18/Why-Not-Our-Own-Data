from typing import List
from .models import QualityScore


class QualityMetrics:
    @staticmethod
    def distribution(scores: List[QualityScore], bins: int = 5) -> dict:
        dist = {f"{(i/bins):.1f}-{((i+1)/bins):.1f}": 0 for i in range(bins)}
        for s in scores:
            for i in range(bins):
                low = i / bins
                high = (i + 1) / bins
                if low <= s.overall < high:
                    dist[f"{low:.1f}-{high:.1f}"] += 1
                    break
        return dist

    @staticmethod
    def report(scores: List[QualityScore]) -> dict:
        if not scores:
            return {"total_scored": 0, "mean_overall": 0, "mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
        import numpy as np
        vals = [s.overall for s in scores]
        return {
            "total_scored": len(scores),
            "mean_overall": round(np.mean(vals), 4),
            "mean": round(np.mean(vals), 4),
            "median": round(float(np.median(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "min": round(float(np.min(vals)), 4),
            "max": round(float(np.max(vals)), 4),
        }
