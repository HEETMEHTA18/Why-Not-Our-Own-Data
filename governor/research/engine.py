import uuid
from datetime import datetime, timezone
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from .models import ResearchTopic, ResearchStatus, PaperSummary, FeasibilityStudy, FeasibilityVerdict, MethodComparison


TOPIC_TEMPLATES = [
    {
        "title": "Optimal LoRA Rank for Coding LLMs",
        "question": "What LoRA rank provides the best trade-off between adaptation quality and parameter efficiency for code generation models?",
        "hypothesis": "A rank of 16-32 provides optimal performance for code tasks, with diminishing returns beyond 64.",
        "methodology": "Train adapters at ranks 4, 8, 16, 32, 64, 128 on same dataset. Evaluate on HumanEval and MBPP. Compare parameter count vs performance gain.",
    },
    {
        "title": "Knowledge Consolidation Strategy: RAG vs Fine-Tuning",
        "question": "When should new coding knowledge be stored in RAG vs fine-tuned into model weights via LoRA?",
        "hypothesis": "Factual/knowledge-intensive updates (APIs, docs) are better as RAG. Reasoning/style updates benefit from fine-tuning.",
        "methodology": "Classify knowledge into factual vs reasoning categories. Apply RAG for one set, LoRA for other. Compare accuracy, latency, and generalization.",
    },
    {
        "title": "Catastrophic Forgetting in Continual Code Learning",
        "question": "How much prior coding knowledge is lost when fine-tuning on new coding standards or frameworks?",
        "hypothesis": "Standard LoRA with 10-20% of training data as replay buffer prevents significant forgetting.",
        "methodology": "Establish baseline on 5 coding benchmarks. Fine-tune on new framework. Measure performance drop on original benchmarks. Test with replay ratios 0%, 5%, 10%, 20%, 50%.",
    },
    {
        "title": "Dataset Quality vs Quantity for Code LLMs",
        "question": "What is the relationship between dataset quality scores and actual model performance improvement?",
        "hypothesis": "Quality-score-filtered datasets (top 20%) outperform unfiltered datasets 3x the size.",
        "methodology": "Build datasets with varying quality thresholds (0.5, 0.7, 0.85, 0.95). Train adapters on each. Measure performance on coding benchmarks. Compare quality-filtered vs size-matched random subsets.",
    },
    {
        "title": "Automated Knowledge Update: When to Trigger Training",
        "question": "What signal threshold justifies triggering a training cycle for a local coding LLM?",
        "hypothesis": "A composite score combining knowledge novelty + user correction frequency + benchmark drift provides a reliable trigger signal.",
        "methodology": "Collect 90 days of usage data. Define trigger signals. Compare against fixed-schedule training (weekly, biweekly, monthly). Measure relevance gain per training cycle.",
    },
    {
        "title": "Multi-Adapter Routing for Diverse Coding Tasks",
        "question": "Can multiple task-specific LoRA adapters outperform a single general adapter for coding tasks?",
        "hypothesis": "A router that selects among adapters (Python, JS, Rust, security, API docs) outperforms a single adapter by 15%+ on per-task benchmarks.",
        "methodology": "Train per-domain adapters. Implement lightweight router (classifier + similarity). Evaluate on mixed-task benchmark vs single general adapter.",
    },
    {
        "title": "Privacy-Preserving Continual Learning from User Corrections",
        "question": "Can user corrections be used for training without storing raw conversation data?",
        "hypothesis": "Differential privacy with epsilon=8 provides reasonable utility while preventing data reconstruction.",
        "methodology": "Implement DP-SGD for LoRA training. Measure utility vs privacy tradeoff at epsilon values 2, 4, 8, 16, 32. Test reconstruction attack resistance.",
    },
]


class ResearchEngine:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_table()

    def _init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS research_topics (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                hypothesis TEXT,
                methodology TEXT,
                status TEXT DEFAULT 'planned',
                findings TEXT DEFAULT '',
                papers_reviewed TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS paper_summaries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT DEFAULT '[]',
                year INTEGER,
                url TEXT,
                abstract TEXT,
                key_findings TEXT,
                relevance REAL DEFAULT 0.0,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS feasibility_studies (
                id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                verdict TEXT NOT NULL,
                rationale TEXT,
                risks TEXT DEFAULT '[]',
                prerequisites TEXT DEFAULT '[]',
                estimated_effort TEXT DEFAULT '',
                recommendations TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS method_comparisons (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                methods TEXT DEFAULT '[]',
                winner TEXT DEFAULT '',
                rationale TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

    def seed_topics(self) -> int:
        existing = self.db.fetchone("SELECT COUNT(*) as c FROM research_topics")["c"]
        if existing > 0:
            return 0
        count = 0
        for tpl in TOPIC_TEMPLATES:
            topic = ResearchTopic(
                id=str(uuid.uuid4()),
                **tpl,
                status=ResearchStatus.PLANNED,
                findings="",
                papers_reviewed=[],
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._save_topic(topic)
            count += 1
        return count

    def _save_topic(self, topic: ResearchTopic):
        self.db.execute(
            """INSERT OR REPLACE INTO research_topics
               (id, title, question, hypothesis, methodology, status, findings, papers_reviewed, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (topic.id, topic.title, topic.question, topic.hypothesis, topic.methodology,
             topic.status.value, topic.findings, str(topic.papers_reviewed),
             topic.created_at, topic.updated_at),
        )

    def list_topics(self, status: Optional[str] = None) -> List[dict]:
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM research_topics WHERE status = ? ORDER BY updated_at DESC", (status,)
            )
        else:
            rows = self.db.fetchall("SELECT * FROM research_topics ORDER BY updated_at DESC")
        return [self._row_to_topic(r) for r in rows]

    def get_topic(self, topic_id: str) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM research_topics WHERE id = ?", (topic_id,))
        return self._row_to_topic(row) if row else None

    def update_topic(self, topic_id: str, **kwargs) -> bool:
        fields = []
        values = []
        for k, v in kwargs.items():
            if k in ("title", "question", "hypothesis", "methodology", "findings"):
                fields.append(f"{k} = ?")
                values.append(v)
            elif k == "status":
                fields.append("status = ?")
                values.append(v.value if isinstance(v, ResearchStatus) else v)
            elif k == "papers_reviewed":
                fields.append("papers_reviewed = ?")
                values.append(str(v))
        if not fields:
            return False
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(topic_id)
        self.db.execute(
            f"UPDATE research_topics SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )
        return True

    def _row_to_topic(self, r: dict) -> dict:
        r["papers_reviewed"] = eval(r.get("papers_reviewed", "[]"))
        return r

    def add_paper(self, title: str, authors: List[str], year: int, url: str,
                  abstract: str, key_findings: str, tags: List[str] = None) -> PaperSummary:
        paper = PaperSummary(
            id=str(uuid.uuid4()),
            title=title,
            authors=authors,
            year=year,
            url=url,
            abstract=abstract,
            key_findings=key_findings,
            relevance=0.0,
            tags=tags or [],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.execute(
            """INSERT OR REPLACE INTO paper_summaries
               (id, title, authors, year, url, abstract, key_findings, relevance, tags, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paper.id, paper.title, str(paper.authors), paper.year, paper.url,
             paper.abstract, paper.key_findings, paper.relevance, str(paper.tags), paper.created_at),
        )
        return paper

    def list_papers(self, limit: int = 50) -> List[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM paper_summaries ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        for r in rows:
            r["authors"] = eval(r.get("authors", "[]"))
            r["tags"] = eval(r.get("tags", "[]"))
        return rows

    def feasibility_study(self, topic_id: str, verdict: FeasibilityVerdict,
                          rationale: str, risks: List[str] = None,
                          prerequisites: List[str] = None,
                          estimated_effort: str = "",
                          recommendations: List[str] = None) -> FeasibilityStudy:
        study = FeasibilityStudy(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            verdict=verdict,
            rationale=rationale,
            risks=risks or [],
            prerequisites=prerequisites or [],
            estimated_effort=estimated_effort,
            recommendations=recommendations or [],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.execute(
            """INSERT OR REPLACE INTO feasibility_studies
               (id, topic_id, verdict, rationale, risks, prerequisites, estimated_effort, recommendations, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (study.id, study.topic_id, study.verdict.value, study.rationale,
             str(study.risks), str(study.prerequisites), study.estimated_effort,
             str(study.recommendations), study.created_at),
        )
        return study

    def list_feasibility(self, topic_id: Optional[str] = None) -> List[dict]:
        if topic_id:
            rows = self.db.fetchall(
                "SELECT * FROM feasibility_studies WHERE topic_id = ? ORDER BY created_at DESC", (topic_id,)
            )
        else:
            rows = self.db.fetchall("SELECT * FROM feasibility_studies ORDER BY created_at DESC")
        for r in rows:
            r["risks"] = eval(r.get("risks", "[]"))
            r["prerequisites"] = eval(r.get("prerequisites", "[]"))
            r["recommendations"] = eval(r.get("recommendations", "[]"))
        return rows

    def stats(self) -> dict:
        topics_total = self.db.fetchone("SELECT COUNT(*) as c FROM research_topics")["c"]
        by_status = self.db.fetchall(
            "SELECT status, COUNT(*) as cnt FROM research_topics GROUP BY status"
        )
        papers = self.db.fetchone("SELECT COUNT(*) as c FROM paper_summaries")["c"]
        studies = self.db.fetchone("SELECT COUNT(*) as c FROM feasibility_studies")["c"]
        return {
            "total_topics": topics_total,
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "total_papers": papers,
            "total_feasibility_studies": studies,
        }
