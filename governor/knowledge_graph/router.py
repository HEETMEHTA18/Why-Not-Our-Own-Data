from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from .engine import KnowledgeGraph
from .models import NodeType, EdgeType, GraphQuery

router = APIRouter(prefix="/kg", tags=["knowledge_graph"])

_kg: Optional[KnowledgeGraph] = None


def get_kg() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg


class AddNodeRequest(BaseModel):
    name: str
    node_type: NodeType
    description: str = ""
    aliases: List[str] = []
    tags: List[str] = []


class AddEdgeRequest(BaseModel):
    source_name: str
    target_name: str
    edge_type: EdgeType
    weight: float = 1.0


@router.get("/")
def list_nodes(node_type: str = None, limit: int = 50):
    kg = get_kg()
    q = GraphQuery(limit=limit)
    if node_type:
        try:
            q.node_type = NodeType(node_type)
        except ValueError:
            pass
    path = kg.query(q)
    return {"nodes": [n.model_dump() for n in path.nodes], "total": len(path.nodes)}


@router.get("/search")
def search_nodes(query: str, node_type: str = None, limit: int = 20):
    kg = get_kg()
    nt = None
    if node_type:
        try:
            nt = NodeType(node_type)
        except ValueError:
            pass
    nodes = kg.search(query, nt, limit)
    return {"results": [n.model_dump() for n in nodes], "count": len(nodes)}


@router.get("/node/{name}")
def get_node(name: str):
    kg = get_kg()
    node = kg.get_node(name)
    if not node:
        raise HTTPException(404, f"Node '{name}' not found")
    connections = kg.get_connections(name)
    return {"node": node.model_dump(), "connections": connections}


@router.post("/node")
def add_node(req: AddNodeRequest):
    kg = get_kg()
    node = kg.add_node(req.name, req.node_type, req.description, req.aliases, req.tags)
    return {"node": node.model_dump()}


@router.post("/edge")
def add_edge(req: AddEdgeRequest):
    kg = get_kg()
    edge = kg.add_edge(req.source_name, req.target_name, req.edge_type, req.weight)
    if not edge:
        raise HTTPException(404, f"Could not find one or both nodes: {req.source_name}, {req.target_name}")
    return {"edge": edge.model_dump()}


@router.get("/path")
def find_path(source: str, target: str, max_depth: int = 4):
    kg = get_kg()
    path = kg.find_path(source, target, max_depth)
    if not path:
        raise HTTPException(404, f"No path found between '{source}' and '{target}'")
    return {
        "nodes": [n.model_dump() for n in path.nodes],
        "edges": [e.model_dump() for e in path.edges],
        "distance": path.total_distance,
    }


@router.get("/stats")
def graph_stats():
    kg = get_kg()
    return kg.get_stats()


@router.get("/connections/{name}")
def get_connections(name: str, edge_type: str = None):
    kg = get_kg()
    et = None
    if edge_type:
        try:
            et = EdgeType(edge_type)
        except ValueError:
            pass
    return {"connections": kg.get_connections(name, et)}


class IngestRequest(BaseModel):
    text: str
    title: str = ""
    knowledge_type: str = ""
    source: str = ""


@router.post("/ingest")
def ingest(req: IngestRequest):
    kg = get_kg()
    return kg.ingest_knowledge(req.text, req.title, req.knowledge_type, req.source)


@router.get("/communities")
def communities():
    kg = get_kg()
    return {"communities": kg.communities()}


@router.get("/emerging")
def emerging(limit: int = 10):
    kg = get_kg()
    return {"topics": kg.emerging_topics(limit)}