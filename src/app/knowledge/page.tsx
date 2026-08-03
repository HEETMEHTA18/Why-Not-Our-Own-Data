"use client"

import { AppShell } from "@/components/layout/app-shell"
import { useState, useEffect } from "react"
import type { ChangeEvent, KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { governor } from "@/lib/api"
import type { KGNode, KGConnection, GovernorDecision, KGEdge } from "@/lib/types"
import { Search, Network, Brain, Database, GitFork, ArrowRight, Layers } from "lucide-react"

const NODE_COLORS: Record<string, string> = {
  language: "text-blue-500",
  framework: "text-green-500",
  library: "text-purple-500",
  tool: "text-orange-500",
  concept: "text-cyan-500",
  pattern: "text-pink-500",
  protocol: "text-yellow-500",
  platform: "text-red-500",
  database: "text-indigo-500",
  standard: "text-teal-500",
  security: "text-rose-500",
  api: "text-violet-500",
}

const ACTION_COLORS: Record<string, string> = {
  ignore: "text-gray-500 bg-gray-100",
  store_rag: "text-blue-500 bg-blue-100",
  store_kg: "text-green-500 bg-green-100",
  recommend_lora: "text-purple-500 bg-purple-100",
}

export default function KnowledgePage() {
  const [nodes, setNodes] = useState<KGNode[]>([])
  const [selectedNode, setSelectedNode] = useState<{ node: KGNode; connections: KGConnection[] } | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<KGNode[]>([])
  const [govStats, setGovStats] = useState<Record<string, unknown> | null>(null)
  const [kgStats, setKgStats] = useState<Record<string, unknown> | null>(null)
  const [govLog, setGovLog] = useState<GovernorDecision[]>([])
  const [pathResult, setPathResult] = useState<{ nodes: KGNode[]; edges: KGEdge[]; distance: number } | null>(null)
  const [pathSource, setPathSource] = useState("")
  const [pathTarget, setPathTarget] = useState("")

  useEffect(() => {
    Promise.all([
      governor.kg.nodes().then(d => setNodes(d.nodes)),
      governor.kg.stats().then(d => setKgStats(d)),
      governor.knowledge.stats().then(d => setGovStats(d)),
      governor.knowledge.log().then(d => setGovLog(d.items)),
    ]).catch(() => {})
  }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    try {
      const res = await governor.kg.search(searchQuery)
      setSearchResults(res.results)
    } catch (e) {}
  }

  const selectNode = async (name: string) => {
    try {
      const res = await governor.kg.node(name)
      setSelectedNode(res)
    } catch (e) {}
  }

  const findPath = async () => {
    if (!pathSource || !pathTarget) return
    try {
      const res = await governor.kg.path(pathSource, pathTarget)
      setPathResult(res)
    } catch (e) {}
  }

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Knowledge & Governance</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Knowledge graph + governance decisions for the coding domain
            </p>
          </div>
        </div>

        {kgStats && govStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card><CardHeader className="py-3"><CardTitle className="text-sm">KG Nodes</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{(kgStats as Record<string, number>).total_nodes || 0}</p></CardContent></Card>
            <Card><CardHeader className="py-3"><CardTitle className="text-sm">KG Edges</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{(kgStats as Record<string, number>).total_edges || 0}</p></CardContent></Card>
            <Card><CardHeader className="py-3"><CardTitle className="text-sm">Governed Items</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{(govStats as Record<string, number>).total_governed || 0}</p></CardContent></Card>
            <Card><CardHeader className="py-3"><CardTitle className="text-sm">Pending LoRA</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold text-purple-500">{(govStats as Record<string, number>).pending_lora || 0}</p></CardContent></Card>
          </div>
        )}

        <Tabs defaultValue="graph">
          <TabsList>
            <TabsTrigger value="graph"><Network className="w-4 h-4 mr-2" />Knowledge Graph</TabsTrigger>
            <TabsTrigger value="governance"><Brain className="w-4 h-4 mr-2" />Governance</TabsTrigger>
            <TabsTrigger value="search"><Search className="w-4 h-4 mr-2" />Search</TabsTrigger>
            <TabsTrigger value="path"><GitFork className="w-4 h-4 mr-2" />Path Finder</TabsTrigger>
          </TabsList>

          <TabsContent value="graph" className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader><CardTitle className="text-sm">Programming Knowledge Graph</CardTitle>
                    <CardDescription>{nodes.length} nodes across knowledge domains</CardDescription></CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[500px]">
                      <div className="space-y-1">
                        {nodes.map(node => (
                          <button
                            key={node.id}
                            className={`w-full text-left px-3 py-2 rounded text-sm hover:bg-accent transition-colors flex items-center gap-2 ${
                              selectedNode?.node.name === node.name ? "bg-accent" : ""
                            }`}
                            onClick={() => selectNode(node.name)}
                          >
                            <span className={`${NODE_COLORS[node.node_type] || "text-gray-500"}`}>
                              <Layers className="w-3.5 h-3.5" />
                            </span>
                            <span className="flex-1">{node.name}</span>
                            <Badge variant="outline" className="text-[10px]">{node.node_type}</Badge>
                          </button>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>

              <div className="lg:col-span-2">
                {selectedNode ? (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <span className={`${NODE_COLORS[selectedNode.node.node_type] || ""}`}>
                          <Layers className="w-5 h-5" />
                        </span>
                        <CardTitle>{selectedNode.node.name}</CardTitle>
                        <Badge>{selectedNode.node.node_type}</Badge>
                      </div>
                      <CardDescription>{selectedNode.node.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <h4 className="text-sm font-medium mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-1 mb-4">
                        {selectedNode.node.tags.map(t => (
                          <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>
                        ))}
                      </div>
                      <h4 className="text-sm font-medium mb-2">Connections ({selectedNode.connections.length})</h4>
                      <div className="space-y-2">
                        {selectedNode.connections.map((conn, i) => (
                          <div key={i} className="flex items-center gap-2 text-sm p-2 bg-muted rounded">
                            <span className="w-16 text-xs text-muted-foreground">
                              {conn.direction === "outgoing" ? "→" : "←"}
                            </span>
                            <span className="font-medium">{conn.connected_to}</span>
                            <Badge variant="outline" className="text-[10px]">{conn.edge_type}</Badge>
                            <Badge variant="secondary" className="text-[10px]">{conn.connected_type}</Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card><CardContent className="py-12 text-center text-muted-foreground">
                    <Network className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    Select a node to view its details and connections
                  </CardContent></Card>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="governance" className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader><CardTitle className="text-sm">Governance Actions</CardTitle></CardHeader>
                  <CardContent>
                    {govStats && (
                      <div className="space-y-3">
                        {Object.entries(govStats as Record<string, unknown>).filter(([k]) => k !== "total_governed" && k !== "applied" && k !== "pending_lora").map(([action, count]) => (
                          <div key={action} className="flex items-center justify-between p-2 rounded bg-muted">
                            <Badge className={ACTION_COLORS[action] || ""}>{action}</Badge>
                            <span className="font-bold">{String(count)}</span>
                          </div>
                        ))}
                        <div className="border-t pt-2">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Applied to dataset</span>
                            <span className="font-bold">{String((govStats as Record<string, number>).applied || 0)}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="lg:col-span-2">
                <Card>
                  <CardHeader><CardTitle className="text-sm">Recent Governance Decisions</CardTitle></CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[500px]">
                      <div className="space-y-2">
                        {govLog.map((g, i) => (
                          <Card key={i}>
                            <CardContent className="py-3">
                              <div className="flex items-center justify-between mb-1">
                                <Badge className={ACTION_COLORS[g.action] || ""}>{g.action}</Badge>
                                <span className="text-xs text-muted-foreground">
                                  {g.governed_at ? new Date(g.governed_at).toLocaleString() : ""}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground mb-1">
                                Confidence: <span className="font-medium">{(g.confidence * 100).toFixed(0)}%</span>
                              </p>
                              <p className="text-sm">{g.reasoning}</p>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="search" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Search Knowledge Graph</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2 mb-4">
                  <Input
                    placeholder="Search for concepts, frameworks, tools..."
                    value={searchQuery}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                    onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && handleSearch()}
                  />
                  <Button onClick={handleSearch}><Search className="w-4 h-4" /></Button>
                </div>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {searchResults.map(node => (
                      <div
                        key={node.id}
                        className="p-3 rounded bg-muted cursor-pointer hover:bg-accent"
                        onClick={() => selectNode(node.name)}
                      >
                        <div className="flex items-center gap-2">
                          <span className={NODE_COLORS[node.node_type] || ""}><Layers className="w-3.5 h-3.5" /></span>
                          <span className="font-medium">{node.name}</span>
                          <Badge variant="outline" className="text-[10px]">{node.node_type}</Badge>
                        </div>
                        {node.description && (
                          <p className="text-xs text-muted-foreground mt-1">{node.description}</p>
                        )}
                        <div className="flex flex-wrap gap-1 mt-1">
                          {node.tags.map(t => (
                            <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="path" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-sm">Find Path Between Concepts</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-4">
                  <Input placeholder="Source (e.g. Python)" value={pathSource} onChange={(e: ChangeEvent<HTMLInputElement>) => setPathSource(e.target.value)} />
                  <Input placeholder="Target (e.g. JWT)" value={pathTarget} onChange={(e: ChangeEvent<HTMLInputElement>) => setPathTarget(e.target.value)} />
                  <Button onClick={findPath}><GitFork className="w-4 h-4 mr-2" />Find Path</Button>
                </div>
                {pathResult && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-3">
                      Distance: {pathResult.distance} edges
                    </p>
                    <div className="space-y-2">
                      {pathResult.nodes.map((node, i) => (
                        <div key={node.id}>
                          <div className="flex items-center gap-2 p-2 bg-muted rounded">
                            <span className={NODE_COLORS[node.node_type] || ""}><Layers className="w-3.5 h-3.5" /></span>
                            <span className="font-medium">{node.name}</span>
                            <Badge variant="outline" className="text-[10px]">{node.node_type}</Badge>
                          </div>
                          {i < pathResult.edges.length && (
                            <div className="flex items-center gap-2 pl-6 py-1">
                              <ArrowRight className="w-3 h-3 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">
                                {pathResult.edges[i]?.edge_type}
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}