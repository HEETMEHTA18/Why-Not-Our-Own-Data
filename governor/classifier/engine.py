import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from ..database.sqlite import SQLiteStore
from .models import KnowledgeCategory, ClassificationVerdict, ClassificationRequest


SIGNAL_PATTERNS = {
    KnowledgeCategory.API_UPDATE: [
        r"\bnew\s+(api|function|method|endpoint|route)\b",
        r"\bdeprecat(ed|ion)\b",
        r"\bapi\s+change",
        r"\badded\s+(support|method|function)",
        r"\bremoved\s+(method|function|api)",
        r"\breplaced\s+by\b",
        r"\brenamed\s+(to|from)\b",
        r"\bnow\s+(accepts|returns|requires)\b",
    ],
    KnowledgeCategory.CODING_STYLE: [
        r"\bcoding\s+style\b",
        r"\bcode\s+review\b",
        r"\blinting?\b",
        r"\bformat(ting|ted)?\b",
        r"\bconvention\b",
        r"\bpattern\b",
        r"\brefactor",
        r"\bidiomatic?\b",
    ],
    KnowledgeCategory.FRAMEWORK: [
        r"\bframework\b",
        r"\breact\b",
        r"\bdjango\b",
        r"\bflask\b",
        r"\bfastapi\b",
        r"\btensorflow\b",
        r"\bpytorch\b",
        r"\blangchain\b",
        r"\bnext[.\s]?js\b",
        r"\bvue\b",
        r"\bspring\b",
        r"\bkubernetes?\b",
        r"\bdocker\b",
    ],
    KnowledgeCategory.REASONING: [
        r"\b(why|how|reason|explain)\b",
        r"\bapproach\b",
        r"\bstrategy\b",
        r"\bmethodology\b",
        r"\bthought\s+process\b",
        r"\bdecision\b",
        r"\btradeoff\b",
        r"\bcompare\b",
    ],
    KnowledgeCategory.BUG_FIX: [
        r"\bfix\w*\b",
        r"\bbug\b",
        r"\berror\b",
        r"\bcrash\b",
        r"\bregression\b",
        r"\bissue\s+#?\d+",
        r"\bhotfix\b",
        r"\bpatch\b",
        r"\bsegfault\b",
        r"\bpanic\b",
        r"\bexception\b",
    ],
    KnowledgeCategory.SECURITY: [
        r"\bcve[-\s]",
        r"\bvulnerabilit",
        r"\bexploit\b",
        r"\battack\b",
        r"\bthreat\b",
        r"\bauth(entication|orization)\b",
        r"\bpermission\b",
        r"\bencrypt\w*\b",
        r"\bsecurity\b",
        r"\bsanitize\b",
        r"\bsqli?\b",
        r"\bxss\b",
        r"\bcsrf\b",
        r"\brce\b",
    ],
    KnowledgeCategory.PERFORMANCE: [
        r"\bperformanc\w+\b",
        r"\boptimize?\w*\b",
        r"\blatency\b",
        r"\bthroughput\b",
        r"\bbottleneck\b",
        r"\bprofiling?\b",
        r"\bmemory\s+(usage|leak|footprint)\b",
        r"\bcpu\b",
        r"\bslow\b",
        r"\bfast\w*\b",
        r"\bcache\b",
    ],
    KnowledgeCategory.CONFIGURATION: [
        r"\bconfigur\w+\b",
        r"\bsetup\b",
        r"\binstall\w*\b",
        r"\benvironment\b",
        r"\benv\b",
        r"\bvariable\b",
        r"\bparameter\b",
        r"\bsetting\b",
        r"\boption\b",
        r"\bflag\b",
        r"\b\.env\b",
        r"\byml\b",
        r"\byaml\b",
        r"\bjson\b",
        r"\btoml\b",
    ],
    KnowledgeCategory.ARCHITECTURE: [
        r"\barchitectur\w+\b",
        r"\bdesign\s+pattern\b",
        r"\bmonolith\b",
        r"\bmicroservice\b",
        r"\bmodular?\b",
        r"\bcomponent\b",
        r"\blayer\b",
        r"\bscalab\w+\b",
        r"\bdecouple\b",
        r"\bcoupling\b",
    ],
    KnowledgeCategory.DEPENDENCY: [
        r"\bdependenc\w+\b",
        r"\bupgrade\b",
        r"\bdowngrade\b",
        r"\bpackage\b",
        r"\bmodule\b",
        r"\blibrar\w+\b",
        r"\bpip\b",
        r"\bnpm\b",
        r"\bcargo\b",
        r"\bgo\s+mod\b",
        r"\bimport\b",
        r"\brequire\b",
    ],
    KnowledgeCategory.DEPRECATION: [
        r"\bdeprecat\w+\b",
        r"\bremoved\b",
        r"\bsunset\b",
        r"\breplaced\s+by\b",
        r"\bwill\s+be\s+removed\b",
        r"\bno\s+longer\s+supported\b",
        r"\bmigrate\s+(from|to)\b",
        r"\blegacy\b",
    ],
    KnowledgeCategory.BEST_PRACTICE: [
        r"\bbest\s+practice\b",
        r"\brecommend\w*\b",
        r"\bshould\b",
        r"\bavoid\b",
        r"\bprefer\b",
        r"\bnever\b",
        r"\balways\b",
        r"\bdon['’]t\b",
        r"\btip\b",
        r"\bguideline\b",
    ],
}


class KnowledgeClassifier:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_table()

    def _init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS classification_verdicts (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                signals TEXT DEFAULT '[]',
                secondary_categories TEXT DEFAULT '[]',
                classified_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_verdicts_item ON classification_verdicts(item_id)
        """)

    def classify_text(self, text: str, title: Optional[str] = None) -> List[Tuple[KnowledgeCategory, float, List[str]]]:
        combined = (title or "") + " " + text
        combined_lower = combined.lower()

        results = []
        for category, patterns in SIGNAL_PATTERNS.items():
            hits = []
            for p in patterns:
                if re.search(p, combined_lower):
                    hits.append(p)
            if hits:
                confidence = min(1.0, 0.3 + (len(hits) * 0.15))
                results.append((category, confidence, hits))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def classify_item(self, item_id: str, text: str, item_type: str = "crawled",
                      title: Optional[str] = None,
                      code_snippets: Optional[List[str]] = None) -> ClassificationVerdict:
        code_text = " ".join(code_snippets) if code_snippets else ""
        full_text = text + " " + code_text

        results = self.classify_text(full_text, title)
        if not results:
            results = [(KnowledgeCategory.BEST_PRACTICE, 0.3, ["default"])]

        primary = results[0]
        secondary = [{"category": c.value, "confidence": round(conf, 4), "signals": sigs}
                     for c, conf, sigs in results[1:4]]

        verdict = ClassificationVerdict(
            id=str(uuid.uuid4()),
            item_id=item_id,
            item_type=item_type,
            category=primary[0],
            confidence=round(primary[1], 4),
            signals=primary[2],
            secondary_categories=secondary,
            classified_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save(verdict)
        return verdict

    def classify_extracted_knowledge(self) -> int:
        rows = self.db.fetchall(
            "SELECT id, title, instruction, output, code_snippets FROM extracted_knowledge"
        )
        count = 0
        for row in rows:
            existing = self.db.fetchone(
                "SELECT id FROM classification_verdicts WHERE item_id = ?", (row["id"],)
            )
            if existing:
                continue
            code = eval(row.get("code_snippets", "[]"))
            self.classify_item(
                item_id=row["id"],
                text=row.get("instruction", "") + " " + row.get("output", ""),
                item_type="extracted_knowledge",
                title=row.get("title"),
                code_snippets=code,
            )
            count += 1
        return count

    def _save(self, verdict: ClassificationVerdict):
        self.db.execute(
            """INSERT OR REPLACE INTO classification_verdicts
               (id, item_id, item_type, category, confidence, signals, secondary_categories, classified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (verdict.id, verdict.item_id, verdict.item_type, verdict.category.value,
             verdict.confidence, str(verdict.signals), str(verdict.secondary_categories),
             verdict.classified_at),
        )

    def get_verdicts(self, category: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[dict]:
        if category:
            rows = self.db.fetchall(
                "SELECT * FROM classification_verdicts WHERE category = ? ORDER BY confidence DESC LIMIT ? OFFSET ?",
                (category, limit, offset),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM classification_verdicts ORDER BY classified_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, r: dict) -> dict:
        r["signals"] = eval(r.get("signals", "[]"))
        r["secondary_categories"] = eval(r.get("secondary_categories", "[]"))
        return r

    def stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM classification_verdicts")["c"]
        by_category = self.db.fetchall(
            "SELECT category, COUNT(*) as cnt FROM classification_verdicts GROUP BY category"
        )
        return {
            "total_classified": total,
            "by_category": {r["category"]: r["cnt"] for r in by_category},
            "categories": [c.value for c in KnowledgeCategory],
        }
