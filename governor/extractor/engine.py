import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from ..database.sqlite import SQLiteStore
from ..crawler.models import CrawledItem
from ..crawler.engine import CrawlerEngine
from .models import ExtractedKnowledge, KnowledgeType
from .parser import HTMLParser


class ExtractionEngine:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.crawler = CrawlerEngine(self.db)
        self._init_table()

    def _init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS extracted_knowledge (
                id TEXT PRIMARY KEY,
                crawled_item_id TEXT NOT NULL,
                knowledge_type TEXT NOT NULL,
                title TEXT NOT NULL,
                instruction TEXT NOT NULL,
                input TEXT DEFAULT '',
                output TEXT NOT NULL,
                source_url TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                language TEXT,
                frameworks TEXT DEFAULT '[]',
                code_snippets TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                in_dataset INTEGER DEFAULT 0
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_type ON extracted_knowledge(knowledge_type)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_item ON extracted_knowledge(crawled_item_id)
        """)

    def extract(self, item: CrawledItem) -> Optional[ExtractedKnowledge]:
        if not item.content or len(item.content.strip()) < 50:
            return None

        code_blocks = HTMLParser.extract_code_blocks(item.content)
        language = HTMLParser.guess_language(item.content)

        knowledge_type = self._classify_knowledge_type(item, code_blocks)
        instruction, input_text, output = self._build_instruction(item, code_blocks, knowledge_type)

        if not instruction or not output:
            return None

        frameworks = self._detect_frameworks(item.content)
        tags = list(set(item.tags + [knowledge_type.value, language] if language else [knowledge_type.value]))

        knowledge = ExtractedKnowledge(
            id=str(uuid.uuid4()),
            crawled_item_id=item.id,
            knowledge_type=knowledge_type,
            title=item.title,
            instruction=instruction,
            input=input_text,
            output=output[:2000],
            source_url=item.url,
            confidence=self._calculate_confidence(item, knowledge_type, code_blocks),
            language=language,
            frameworks=frameworks,
            code_snippets=[b["code"] for b in code_blocks[:5]],
            tags=tags,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "source": item.source.value,
                "author": item.author,
                "published": item.published,
                "has_code": len(code_blocks) > 0,
            },
        )

        self._save(knowledge)
        self.crawler.mark_extracted(item.id)
        return knowledge

    def extract_many(self, items: List[CrawledItem]) -> List[ExtractedKnowledge]:
        return [e for item in items if (e := self.extract(item)) is not None]

    def extract_unextracted(self, limit: int = 50) -> List[ExtractedKnowledge]:
        items = self.crawler.get_unextracted(limit=limit)
        return self.extract_many(items)

    def _classify_knowledge_type(self, item: CrawledItem, code_blocks: list) -> KnowledgeType:
        text = (item.title + " " + item.content).lower()
        source = item.source.value

        security_keywords = ["cve", "vulnerability", "security", "exploit", "patch", "fix security"]
        if any(kw in text for kw in security_keywords):
            return KnowledgeType.SECURITY

        bug_keywords = ["bug fix", "fixed", "fixes", "hotfix", "regression", "issue #"]
        if any(kw in text for kw in bug_keywords):
            return KnowledgeType.BUG_FIX

        api_keywords = ["api", "endpoint", "deprecated", "deprecation", "new function", "new method", "added"]
        if any(kw in text for kw in api_keywords):
            return KnowledgeType.API_UPDATE

        deprecation_keywords = ["deprecated", "removed", "sunset", "replaced by", "will be removed"]
        if any(kw in text for kw in deprecation_keywords):
            return KnowledgeType.DEPRECATION

        perf_keywords = ["performance", "optimization", "faster", "memory", "latency", "throughput"]
        if any(kw in text for kw in perf_keywords):
            return KnowledgeType.PERFORMANCE

        config_keywords = ["configuration", "config", "setup", "installation", "environment"]
        if any(kw in text for kw in config_keywords):
            return KnowledgeType.CONFIGURATION

        arch_keywords = ["architecture", "design pattern", "refactor", "restructure"]
        if any(kw in text for kw in arch_keywords):
            return KnowledgeType.ARCHITECTURE

        if code_blocks:
            code = " ".join(b["code"] for b in code_blocks).lower()
            if any(kw in code for kw in ["import ", "from ", "require("]):
                lang = HTMLParser.guess_language(code)
                if lang:
                    return KnowledgeType.CODING_STYLE

        if source in ("rfc", "language_spec"):
            return KnowledgeType.FRAMEWORK

        if len(text.split()) > 200 and "?" not in text:
            return KnowledgeType.REASONING

        return KnowledgeType.BEST_PRACTICE

    def _build_instruction(self, item: CrawledItem, code_blocks: list, ktype: KnowledgeType) -> Tuple[str, str, str]:
        type_prompts = {
            KnowledgeType.API_UPDATE: ("Explain the API change for", "What changed in this API update?"),
            KnowledgeType.CODING_STYLE: ("Show me how to", "How should I write this?"),
            KnowledgeType.FRAMEWORK: ("Explain how to use", "What does this framework do?"),
            KnowledgeType.REASONING: ("Walk through the reasoning for", "Explain the thinking behind this approach."),
            KnowledgeType.BUG_FIX: ("How do I fix", "What caused this bug and how was it fixed?"),
            KnowledgeType.SECURITY: ("How do I address", "What security issue was found and how is it mitigated?"),
            KnowledgeType.PERFORMANCE: ("Optimize", "How can I improve performance?"),
            KnowledgeType.CONFIGURATION: ("Configure", "How do I configure this?"),
            KnowledgeType.ARCHITECTURE: ("Design", "What architecture pattern is used?"),
            KnowledgeType.DEPENDENCY: ("Add", "What dependency changed and how does it affect my project?"),
            KnowledgeType.DEPRECATION: ("Replace", "What was deprecated and what should I use instead?"),
            KnowledgeType.BEST_PRACTICE: ("What is the best practice for", "What approach should I follow?"),
        }

        prefix, default_input = type_prompts.get(ktype, ("Explain", "What does this mean?"))

        if code_blocks:
            code_text = "\n".join(b["code"] for b in code_blocks[:3])
            if len(code_text) > 1500:
                code_text = code_text[:1500] + "..."
            instruction = f"{prefix} {item.title} in {ktype.value.replace('_', ' ')}"
            input_text = f"Context: {item.summary[:500]}"
            output = f"Here's how:\n\n```{code_blocks[0]['language']}\n{code_text}\n```\n\n{item.summary[:500]}"
        else:
            instruction = f"{prefix} {item.title}"
            input_text = default_input
            output = item.summary[:1000]

        return instruction[:500], input_text[:500], output[:2000]

    def _detect_frameworks(self, text: str) -> List[str]:
        frameworks = []
        known = [
            "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask",
            "fastapi", "spring", "spring boot", "tensorflow", "pytorch", "jax", "langchain",
            "llamaindex", "huggingface", "transformers", "ollama", "vllm", "triton",
            "kubernetes", "docker", "terraform", "ansible", "express", "tailwind",
            "typescript", "rust", "tokio", "actix", "axum", "sqlalchemy", "prisma",
        ]
        text_lower = text.lower()
        for fw in known:
            if fw in text_lower:
                frameworks.append(fw)
        return frameworks[:10]

    def _calculate_confidence(self, item: CrawledItem, ktype: KnowledgeType, code_blocks: list) -> float:
        score = 0.5
        if item.author:
            score += 0.1
        if code_blocks:
            score += 0.15
        if ktype in (KnowledgeType.SECURITY, KnowledgeType.BUG_FIX, KnowledgeType.API_UPDATE):
            score += 0.1
        if item.source in ("github_release", "changelog"):
            score += 0.1
        if len(item.content) > 500:
            score += 0.05
        return min(1.0, score)

    def _save(self, knowledge: ExtractedKnowledge):
        self.db.execute(
            """INSERT OR REPLACE INTO extracted_knowledge
               (id, crawled_item_id, knowledge_type, title, instruction, input, output,
                source_url, confidence, language, frameworks, code_snippets, tags, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (knowledge.id, knowledge.crawled_item_id, knowledge.knowledge_type.value,
             knowledge.title, knowledge.instruction, knowledge.input, knowledge.output,
             knowledge.source_url, knowledge.confidence, knowledge.language,
             str(knowledge.frameworks), str(knowledge.code_snippets),
             str(knowledge.tags), knowledge.created_at, str(knowledge.metadata)),
        )

    def list_knowledge(self, knowledge_type: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[dict]:
        if knowledge_type:
            rows = self.db.fetchall(
                "SELECT * FROM extracted_knowledge WHERE knowledge_type = ? ORDER BY confidence DESC LIMIT ? OFFSET ?",
                (knowledge_type, limit, offset),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM extracted_knowledge ORDER BY confidence DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, r: dict) -> dict:
        r["frameworks"] = eval(r.get("frameworks", "[]"))
        r["code_snippets"] = eval(r.get("code_snippets", "[]"))
        r["tags"] = eval(r.get("tags", "[]"))
        r["metadata"] = eval(r.get("metadata", "{}"))
        return r

    def stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM extracted_knowledge")["c"]
        by_type = self.db.fetchall(
            "SELECT knowledge_type, COUNT(*) as cnt FROM extracted_knowledge GROUP BY knowledge_type"
        )
        by_language = self.db.fetchall(
            "SELECT language, COUNT(*) as cnt FROM extracted_knowledge WHERE language IS NOT NULL GROUP BY language"
        )
        in_dataset = self.db.fetchone("SELECT COUNT(*) as c FROM extracted_knowledge WHERE in_dataset = 1")["c"]
        return {
            "total_extracted": total,
            "in_dataset": in_dataset,
            "by_type": {r["knowledge_type"]: r["cnt"] for r in by_type},
            "by_language": {r["language"]: r["cnt"] for r in by_language},
        }

    def push_to_dataset(self, knowledge_id: str) -> bool:
        row = self.db.fetchone("SELECT * FROM extracted_knowledge WHERE id = ?", (knowledge_id,))
        if not row:
            return False
        d = self._row_to_dict(row)
        from ..dataset.builder import DatasetBuilder
        from ..dataset.models import InstructionExample
        builder = DatasetBuilder(self.db)
        example = InstructionExample(
            id=str(uuid.uuid4()),
            conversation_id=d["crawled_item_id"],
            instruction=d["instruction"],
            input=d["input"],
            output=d["output"],
            source=f"crawled_{d['knowledge_type']}",
            created_at=datetime.now(timezone.utc).isoformat(),
            quality_score=d["confidence"],
            is_valid=True,
            metadata={"knowledge_id": knowledge_id, "source_url": d["source_url"], "knowledge_type": d["knowledge_type"]},
        )
        builder._save_example(example)
        self.db.execute("UPDATE extracted_knowledge SET in_dataset = 1 WHERE id = ?", (knowledge_id,))
        return True
