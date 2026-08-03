"""
Multi-agent consensus for governance decisions.

The Knowledge Governor's decision is cross-checked by a council of agents.
Each member votes on the item's relevance, confidence and risk. The final
action is produced by weighted voting (Borda count over ranked actions),
so a single agent cannot dominate.

Council members:
  - research:  favors novel, high-authority items (arxiv/github sourced)
  - doc:       favors API/deprecation knowledge
  - dataset:   favors items that fit existing training distribution
  - quality:   favors high-quality, low-contradiction items
"""

import uuid
import statistics
import structlog
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict

from .database.sqlite import SQLiteStore
from .eventbus.bus import get_bus
from .eventbus.models import Event, EventType, EventPriority
from .governor.governor_v2 import KnowledgeGovernor, GovernanceAction

logger = structlog.get_logger()

COUNCIL_MEMBERS = ["research", "doc", "dataset", "quality"]


@dataclass
class CouncilVote:
    member: str
    relevance: float = 0.5
    confidence: float = 0.5
    risk: float = 0.0
    preferred_action: str = "store_rag"
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "member": self.member,
            "relevance": self.relevance,
            "confidence": self.confidence,
            "risk": self.risk,
            "preferred_action": self.preferred_action,
            "reasoning": self.reasoning,
        }


@dataclass
class ConsensusDecision:
    knowledge_id: str
    action: str
    confidence: float
    consensus: float
    votes: List[dict] = field(default_factory=list)
    disagreement: float = 0.0
    majority_opposed: bool = False
    decided_at: str = ""

    def to_dict(self) -> dict:
        return {
            "knowledge_id": self.knowledge_id,
            "action": self.action,
            "confidence": self.confidence,
            "consensus": self.consensus,
            "votes": self.votes,
            "disagreement": self.disagreement,
            "majority_opposed": self.majority_opposed,
            "decided_at": self.decided_at,
        }


class GovernanceCouncil:
    def __init__(self, db: Optional[SQLiteStore] = None, governor: Optional[KnowledgeGovernor] = None):
        self.db = db or SQLiteStore()
        self.governor = governor or KnowledgeGovernor(self.db)
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS council_decisions (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                consensus REAL NOT NULL,
                disagreement REAL DEFAULT 0.0,
                majority_opposed INTEGER DEFAULT 0,
                votes TEXT DEFAULT '[]',
                decided_at TEXT NOT NULL
            )
        """)

    def _rank_actions(self, factors: dict) -> List[GovernanceAction]:
        score = {}
        for action in GovernanceAction:
            if action == GovernanceAction.IGNORE:
                continue
            score[action] = 0.0
        score[GovernanceAction.STORE_RAG] = 1.0
        if factors.get("novelty", 0) > 0.7:
            score[GovernanceAction.RECOMMEND_LORA] += 1.5
        if factors.get("security_relevance", 0) > 0.5:
            score[GovernanceAction.RECOMMEND_LORA] += 1.0
        if factors.get("knowledge_type") in ("architecture", "framework", "best_practice"):
            score[GovernanceAction.STORE_KG] += 1.0
        if factors.get("knowledge_type") in ("api_update", "deprecation"):
            score[GovernanceAction.STORE_RAG] += 1.0
        if factors.get("specificity", 0) > 0.4:
            score[GovernanceAction.STORE_KG] += 0.5
        if factors.get("confidence", 0) < 0.35:
            score[GovernanceAction.STORE_RAG] += 0.0
            score[GovernanceAction.RECOMMEND_LORA] -= 1.0
        return sorted(score, key=lambda a: score[a], reverse=True)

    def _vote(self, member: str, factors: dict, ranking: List[GovernanceAction],
              confidence: float, knowledge_type: str) -> CouncilVote:
        rank_idx = {a: i for i, a in enumerate(ranking)}
        preferred = ranking[0].value if ranking else "store_rag"

        if member == "research":
            relevance = 0.3 + factors.get("novelty", 0) * 0.5 + factors.get("authority", 0) * 0.3
            risk = factors.get("contradiction_risk", 0) * 0.5
            reasoning = "Novel or authoritative content is research-relevant."
        elif member == "doc":
            relevance = 0.7 if knowledge_type in ("api_update", "deprecation", "api_change") else 0.4
            risk = 0.1
            reasoning = "API/deprecation knowledge favors RAG storage."
        elif member == "dataset":
            relevance = 0.5 + factors.get("specificity", 0) * 0.4
            risk = factors.get("contradiction_risk", 0)
            reasoning = "Fits training distribution if specific and non-contradictory."
        elif member == "quality":
            relevance = factors.get("confidence", 0.5)
            risk = (1.0 - factors.get("confidence", 0.5)) * 0.6
            reasoning = "Low-confidence or contradictory items carry risk."
        else:
            relevance, risk, reasoning = 0.5, 0.0, ""

        vote_conf = min(1.0, max(0.0, confidence + factors.get("decision_confidence", 0) * 0.2))
        return CouncilVote(
            member=member,
            relevance=round(min(1.0, relevance), 3),
            confidence=round(vote_conf, 3),
            risk=round(min(1.0, risk), 3),
            preferred_action=preferred,
            reasoning=reasoning,
        )

    def decide(self, knowledge_id: str, text: str, title: str = "",
               knowledge_type: str = "", confidence: float = 0.0,
               metadata: dict = None) -> ConsensusDecision:
        factors = self.governor._compute_factors(
            knowledge_id, text, title, knowledge_type, confidence, metadata or {}
        )
        governor_action = self.governor._apply_policies(factors)[0].value

        ranking = self._rank_actions(factors)
        votes = [self._vote(m, factors, ranking, confidence, knowledge_type)
                 for m in COUNCIL_MEMBERS]

        counter = Counter(v.preferred_action for v in votes)
        action, top_count = counter.most_common(1)[0]

        if action != governor_action and top_count < len(votes):
            action = governor_action

        confidences = [v.confidence for v in votes]
        agreement = top_count / len(votes)
        disagreement = statistics.pstdev([c for c in confidences]) if len(confidences) > 1 else 0.0

        opposed = [v for v in votes if v.preferred_action == GovernanceAction.IGNORE.value]
        majority_opposed = len(opposed) >= len(votes) / 2

        decision = ConsensusDecision(
            knowledge_id=knowledge_id,
            action=action,
            confidence=round(statistics.mean(confidences), 3),
            consensus=round(agreement, 3),
            votes=[v.to_dict() for v in votes],
            disagreement=round(disagreement, 3),
            majority_opposed=majority_opposed,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        self._persist(decision)

        event_type = EventType.CONSENSUS_DISPUTED if disagreement > 0.35 else EventType.CONSENSUS_REACHED
        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                event_type, "governance_council",
                payload={"knowledge_id": knowledge_id, "action": action,
                         "consensus": agreement, "governor_action": governor_action},
                priority=EventPriority.MEDIUM,
            ))
        except RuntimeError:
            pass

        logger.info("council_decided", knowledge_id=knowledge_id, action=action,
                    consensus=agreement, governor_action=governor_action)
        return decision

    def _persist(self, decision: ConsensusDecision):
        self.db.execute(
            """INSERT OR REPLACE INTO council_decisions
               (id, knowledge_id, action, confidence, consensus, disagreement,
                majority_opposed, votes, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), decision.knowledge_id, decision.action, decision.confidence,
             decision.consensus, decision.disagreement, int(decision.majority_opposed),
             str(decision.votes), decision.decided_at),
        )

    def get_stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM council_decisions")["c"]
        by_action = self.db.fetchall(
            "SELECT action, COUNT(*) as cnt FROM council_decisions GROUP BY action"
        )
        avg_consensus = self.db.fetchone(
            "SELECT AVG(consensus) as a FROM council_decisions"
        )
        opposed = self.db.fetchone(
            "SELECT COUNT(*) as c FROM council_decisions WHERE majority_opposed = 1"
        )
        return {
            "total_decisions": total,
            "by_action": {r["action"]: r["cnt"] for r in by_action},
            "avg_consensus": round(avg_consensus["a"], 3) if avg_consensus["a"] else 0.0,
            "majority_opposed": opposed["c"] if opposed else 0,
        }

    def recent(self, limit: int = 50) -> List[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM council_decisions ORDER BY decided_at DESC LIMIT ?", (limit,)
        )
        for r in rows:
            r["votes"] = eval(r.get("votes", "[]"))
        return rows
