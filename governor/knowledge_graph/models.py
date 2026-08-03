from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class NodeType(str, Enum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    TOOL = "tool"
    CONCEPT = "concept"
    PATTERN = "pattern"
    PROTOCOL = "protocol"
    PLATFORM = "platform"
    PARADIGM = "paradigm"
    STANDARD = "standard"
    SECURITY = "security"
    DATABASE = "database"
    API = "api"


class EdgeType(str, Enum):
    USES = "uses"
    BUILT_ON = "built_on"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    ALTERNATIVE_TO = "alternative_to"
    REQUIRES = "requires"
    REPLACES = "replaces"
    KNOWLEDGE_ABOUT = "knowledge_about"


class KnowledgeNode(BaseModel):
    id: str
    name: str
    node_type: NodeType
    description: str = ""
    aliases: List[str] = []
    tags: List[str] = []
    metadata: dict = {}
    created_at: str = ""


class KnowledgeEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: dict = {}
    created_at: str = ""


class GraphQuery(BaseModel):
    source_name: Optional[str] = None
    node_type: Optional[NodeType] = None
    max_depth: int = 2
    limit: int = 50


class GraphPath(BaseModel):
    nodes: List[KnowledgeNode]
    edges: List[KnowledgeEdge]
    total_distance: float = 0.0


KG_SEED_NODES = [
    {"name": "Python", "node_type": NodeType.LANGUAGE, "tags": ["general-purpose", "interpreted", "dynamic"]},
    {"name": "JavaScript", "node_type": NodeType.LANGUAGE, "tags": ["interpreted", "event-driven", "prototype-based"]},
    {"name": "TypeScript", "node_type": NodeType.LANGUAGE, "tags": ["typed", "compiled", "superset"]},
    {"name": "Rust", "node_type": NodeType.LANGUAGE, "tags": ["systems", "memory-safe", "concurrent"]},
    {"name": "Go", "node_type": NodeType.LANGUAGE, "tags": ["compiled", "concurrent", "static"]},
    {"name": "FastAPI", "node_type": NodeType.FRAMEWORK, "tags": ["async", "python", "rest", "openapi"]},
    {"name": "Django", "node_type": NodeType.FRAMEWORK, "tags": ["python", "full-stack", "orm"]},
    {"name": "Flask", "node_type": NodeType.FRAMEWORK, "tags": ["python", "micro", "wsgi"]},
    {"name": "React", "node_type": NodeType.FRAMEWORK, "tags": ["javascript", "ui", "component", "spa"]},
    {"name": "Next.js", "node_type": NodeType.FRAMEWORK, "tags": ["react", "ssr", "static", "full-stack"]},
    {"name": "Vue", "node_type": NodeType.FRAMEWORK, "tags": ["javascript", "reactive", "component"]},
    {"name": "Docker", "node_type": NodeType.TOOL, "tags": ["container", "deployment", "devops"]},
    {"name": "Kubernetes", "node_type": NodeType.PLATFORM, "tags": ["orchestration", "container", "scaling"]},
    {"name": "PostgreSQL", "node_type": NodeType.DATABASE, "tags": ["relational", "sql", "acid"]},
    {"name": "SQLite", "node_type": NodeType.DATABASE, "tags": ["embedded", "lightweight", "sql"]},
    {"name": "Redis", "node_type": NodeType.DATABASE, "tags": ["in-memory", "cache", "key-value", "pub-sub"]},
    {"name": "DuckDB", "node_type": NodeType.DATABASE, "tags": ["embedded", "analytics", "olap", "columnar"]},
    {"name": "Ollama", "node_type": NodeType.TOOL, "tags": ["llm", "local", "inference"]},
    {"name": "PyTorch", "node_type": NodeType.LIBRARY, "tags": ["ml", "deep-learning", "tensor"]},
    {"name": "Transformers", "node_type": NodeType.LIBRARY, "tags": ["nlp", "huggingface", "llm"]},
    {"name": "PEFT", "node_type": NodeType.LIBRARY, "tags": ["fine-tuning", "lora", "efficient"]},
    {"name": "Unsloth", "node_type": NodeType.TOOL, "tags": ["fine-tuning", "optimized", "lora"]},
    {"name": "LangChain", "node_type": NodeType.LIBRARY, "tags": ["llm", "pipeline", "agent"]},
    {"name": "SQLAlchemy", "node_type": NodeType.LIBRARY, "tags": ["orm", "python", "database"]},
    {"name": "pydantic", "node_type": NodeType.LIBRARY, "tags": ["validation", "python", "typing"]},
    {"name": "Dependency Injection", "node_type": NodeType.CONCEPT, "tags": ["pattern", "ioc", "decoupling"]},
    {"name": "REST API", "node_type": NodeType.CONCEPT, "tags": ["api", "http", "stateless"]},
    {"name": "GraphQL", "node_type": NodeType.PROTOCOL, "tags": ["api", "query", "typed"]},
    {"name": "WebSocket", "node_type": NodeType.PROTOCOL, "tags": ["real-time", "bidirectional", "event-driven"]},
    {"name": "OAuth2", "node_type": NodeType.STANDARD, "tags": ["authentication", "authorization", "security"]},
    {"name": "JWT", "node_type": NodeType.STANDARD, "tags": ["token", "authentication", "stateless"]},
    {"name": "HTTPS", "node_type": NodeType.PROTOCOL, "tags": ["security", "encryption", "tls"]},
    {"name": "GitHub Actions", "node_type": NodeType.TOOL, "tags": ["ci-cd", "automation", "devops"]},
    {"name": "Prometheus", "node_type": NodeType.TOOL, "tags": ["monitoring", "metrics", "observability"]},
    {"name": "Async/Await", "node_type": NodeType.CONCEPT, "tags": ["concurrency", "async", "event-loop"]},
    {"name": "Microservices", "node_type": NodeType.PATTERN, "tags": ["architecture", "distributed", "scalability"]},
    {"name": "LoRA", "node_type": NodeType.CONCEPT, "tags": ["fine-tuning", "efficient", "adapters"]},
    {"name": "RAG", "node_type": NodeType.PATTERN, "tags": ["retrieval", "generation", "knowledge"]},
    {"name": "CI/CD", "node_type": NodeType.CONCEPT, "tags": ["automation", "deployment", "testing"]},
    {"name": "TDD", "node_type": NodeType.PATTERN, "tags": ["testing", "development", "quality"]},
    {"name": "MVC", "node_type": NodeType.PATTERN, "tags": ["architecture", "separation", "design"]},
    {"name": "Design Patterns", "node_type": NodeType.CONCEPT, "tags": ["architecture", "reusability", "best-practices"]},
    {"name": "Docker Compose", "node_type": NodeType.TOOL, "tags": ["docker", "multi-container", "devops"]},
    {"name": "Nginx", "node_type": NodeType.TOOL, "tags": ["reverse-proxy", "web-server", "load-balancer"]},
    {"name": "AWS", "node_type": NodeType.PLATFORM, "tags": ["cloud", "infrastructure", "iaas"]},
    {"name": "OpenAPI", "node_type": NodeType.STANDARD, "tags": ["api", "specification", "documentation"]},
    {"name": "WebSockets", "node_type": NodeType.PROTOCOL, "tags": ["real-time", "bidirectional", "push"]},
    {"name": "gRPC", "node_type": NodeType.PROTOCOL, "tags": ["rpc", "protobuf", "high-performance"]},
    {"name": "SQL", "node_type": NodeType.LANGUAGE, "tags": ["query", "relational", "declarative"]},
    {"name": "HTML/CSS", "node_type": NodeType.LANGUAGE, "tags": ["web", "markup", "styling"]},
]

KG_SEED_EDGES = [
    # Language -> Framework
    ("Python", "FastAPI", EdgeType.USES), ("Python", "Django", EdgeType.USES), ("Python", "Flask", EdgeType.USES),
    ("Python", "SQLAlchemy", EdgeType.USES), ("Python", "LangChain", EdgeType.USES),
    ("Python", "PyTorch", EdgeType.USES), ("Python", "pydantic", EdgeType.USES),
    ("JavaScript", "React", EdgeType.USES), ("JavaScript", "Vue", EdgeType.USES),
    ("TypeScript", "React", EdgeType.USES), ("TypeScript", "Next.js", EdgeType.USES),
    # Framework -> Library/Tool
    ("React", "Next.js", EdgeType.BUILT_ON), ("FastAPI", "pydantic", EdgeType.USES),
    ("FastAPI", "SQLAlchemy", EdgeType.USES), ("FastAPI", "OAuth2", EdgeType.USES),
    ("FastAPI", "OpenAPI", EdgeType.IMPLEMENTS), ("Django", "SQLAlchemy", EdgeType.ALTERNATIVE_TO),
    ("Next.js", "React", EdgeType.BUILT_ON),
    # Tool -> Concept
    ("Docker", "Kubernetes", EdgeType.RELATED_TO), ("Docker", "Docker Compose", EdgeType.EXTENDS),
    ("Kubernetes", "Docker", EdgeType.REQUIRES), ("GitHub Actions", "CI/CD", EdgeType.IMPLEMENTS),
    # Concept -> Concept
    ("Async/Await", "FastAPI", EdgeType.USES), ("Dependency Injection", "FastAPI", EdgeType.USES),
    ("LoRA", "PEFT", EdgeType.IMPLEMENTS), ("LoRA", "Unsloth", EdgeType.IMPLEMENTS),
    ("RAG", "LangChain", EdgeType.IMPLEMENTS), ("RAG", "Transformers", EdgeType.USES),
    ("OAuth2", "JWT", EdgeType.RELATED_TO), ("OAuth2", "HTTPS", EdgeType.REQUIRES),
    ("Microservices", "Docker", EdgeType.USES), ("Microservices", "Kubernetes", EdgeType.USES),
    ("MVC", "Django", EdgeType.IMPLEMENTS), ("REST API", "OpenAPI", EdgeType.RELATED_TO),
    ("GraphQL", "REST API", EdgeType.ALTERNATIVE_TO),
    # Database -> Framework
    ("PostgreSQL", "SQLAlchemy", EdgeType.USES), ("PostgreSQL", "Django", EdgeType.USES),
    ("Redis", "FastAPI", EdgeType.USES), ("SQLite", "DuckDB", EdgeType.ALTERNATIVE_TO),
    # LLM ecosystem
    ("Ollama", "Transformers", EdgeType.ALTERNATIVE_TO), ("Ollama", "LangChain", EdgeType.USES),
    ("PyTorch", "Transformers", EdgeType.BUILT_ON), ("PyTorch", "Unsloth", EdgeType.BUILT_ON),
    ("Transformers", "PEFT", EdgeType.EXTENDS),
    # Lang relationships
    ("TypeScript", "JavaScript", EdgeType.EXTENDS), ("Python", "SQL", EdgeType.USES),
]