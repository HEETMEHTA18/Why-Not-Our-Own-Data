"use client"

import { AppShell } from "@/components/layout/app-shell"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { platform, governor } from "@/lib/api"
import type { RouteResult, TelemetryStats, ProfileResult } from "@/lib/types"
import { GitBranch, Database, Activity, AlertTriangle, User, Send } from "lucide-react"

export default function IntelligencePage() {
  const [routePrompt, setRoutePrompt] = useState("")
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null)
  const [ragQuery, setRagQuery] = useState("")
  const [ragDocs, setRagDocs] = useState<Record<string, unknown>[]>([])
  const [ragStats, setRagStats] = useState<Record<string, unknown> | null>(null)
  const [telemetry, setTelemetry] = useState<TelemetryStats | null>(null)
  const [alerts, setAlerts] = useState<Record<string, unknown>[]>([])
  const [profile, setProfile] = useState<ProfileResult | null>(null)
  const [communities, setCommunities] = useState<Record<string, unknown>[]>([])
  const [kgStats, setKgStats] = useState<Record<string, unknown> | null>(null)

  const fetchData = async () => {
    try {
      const [t, a, p, c, k, rs] = await Promise.all([
        platform.telemetry.stats(),
        platform.alerts.list(),
        platform.profiler.profile(),
        platform.kg.communities(),
        governor.kg.stats(),
        platform.rag.stats(),
      ])
      setTelemetry(t)
      setAlerts(a.alerts)
      setProfile(p)
      setCommunities(c.communities)
      setKgStats(k)
      setRagStats(rs)
    } catch (e) {
      console.error("Failed to fetch intelligence data", e)
    }
  }

  useEffect(() => { fetchData() }, [])

  const doRoute = async () => {
    if (!routePrompt) return
    try {
      const r = await platform.routing.route(routePrompt)
      setRouteResult(r)
    } catch (e) { console.error(e) }
  }

  const doRag = async () => {
    if (!ragQuery) return
    try {
      const r = await platform.rag.retrieve(ragQuery)
      setRagDocs(r.documents)
    } catch (e) { console.error(e) }
  }

  const ingestKb = async () => {
    try {
      await platform.kg.ingest({
        text: "FastAPI uses pydantic for request validation and SQLAlchemy for database ORM. Docker containers package FastAPI services for Kubernetes deployment.",
        title: "FastAPI stack", knowledge_type: "framework",
      })
      fetchData()
    } catch (e) { console.error(e) }
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Intelligence</h1>
            <p className="text-sm text-muted-foreground">Routing, RAG, lineage, cost, alerts and profiling</p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData}>Refresh</Button>
        </div>

        <Tabs defaultValue="routing">
          <TabsList>
            <TabsTrigger value="routing">Adapter Routing</TabsTrigger>
            <TabsTrigger value="rag">RAG Knowledge</TabsTrigger>
            <TabsTrigger value="kg">Knowledge Graph</TabsTrigger>
            <TabsTrigger value="cost">Cost & ROI</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="profile">Profiler</TabsTrigger>
          </TabsList>

          <TabsContent value="routing" className="mt-4 space-y-3">
            <Card>
              <CardContent className="pt-4">
                <div className="flex gap-2">
                  <Input placeholder="Enter a prompt to route to the best adapter..." value={routePrompt} onChange={e => setRoutePrompt(e.target.value)} />
                  <Button onClick={doRoute} disabled={!routePrompt}><Send className="w-3.5 h-3.5 mr-1.5" /> Route</Button>
                </div>
                {routeResult && (
                  <div className="mt-4 p-4 rounded-lg bg-muted">
                    <div className="flex items-center gap-2 mb-2">
                      <GitBranch className="w-4 h-4 text-primary" />
                      <span className="text-sm font-semibold">Domain: {routeResult.domain}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 rounded bg-background">
                        <span className="text-[10px] text-muted-foreground block">Chosen</span>
                        <span className="text-sm font-bold">{routeResult.chosen_adapter.adapter_id}</span>
                      </div>
                      <div className="p-2 rounded bg-background">
                        <span className="text-[10px] text-muted-foreground block">Benchmark</span>
                        <span className="text-sm font-bold">{routeResult.chosen_adapter.benchmark_score}</span>
                      </div>
                      <div className="p-2 rounded bg-background">
                        <span className="text-[10px] text-muted-foreground block">Improvement</span>
                        <span className="text-sm font-bold text-emerald-600">+{routeResult.chosen_adapter.improvement}</span>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="rag" className="mt-4 space-y-3">
            <Card>
              <CardContent className="pt-4">
                <div className="flex gap-2">
                  <Input placeholder="Query the RAG knowledge base..." value={ragQuery} onChange={e => setRagQuery(e.target.value)} />
                  <Button onClick={doRag} disabled={!ragQuery}>Retrieve</Button>
                </div>
                {ragStats && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {String((ragStats as Record<string, unknown>).total_documents ?? 0)} documents stored
                  </p>
                )}
                <div className="mt-3 space-y-2">
                  {ragDocs.map((d, i) => (
                    <div key={i} className="p-3 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{String(d.title)}</span>
                        <Badge variant="outline" className="text-[10px]">{String(d.knowledge_type)}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{String(d.content)}</p>
                      <span className="text-[10px] text-muted-foreground">score {String(d.relevance_score)}</span>
                    </div>
                  ))}
                  {ragDocs.length === 0 && ragQuery && (
                    <p className="text-xs text-muted-foreground">No relevant documents found.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="kg" className="mt-4 space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card><CardHeader className="pb-2"><CardDescription>Nodes</CardDescription><CardTitle className="text-xl">{String((kgStats as Record<string, unknown> | null)?.total_nodes ?? "—")}</CardTitle></CardHeader></Card>
              <Card><CardHeader className="pb-2"><CardDescription>Edges</CardDescription><CardTitle className="text-xl">{String((kgStats as Record<string, unknown> | null)?.total_edges ?? "—")}</CardTitle></CardHeader></Card>
            </div>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2"><Database className="w-4 h-4 text-primary" /> Community Detection</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {communities.slice(0, 6).map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded bg-muted text-sm">
                      <span className="font-medium">{String(c.label)}</span>
                      <Badge variant="secondary">{String(c.size)} members</Badge>
                    </div>
                  ))}
                </div>
                <Button size="sm" variant="outline" className="mt-3" onClick={ingestKb}>Ingest sample knowledge</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="cost" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2"><Activity className="w-4 h-4 text-primary" /> GPU Cost & ROI</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 rounded bg-muted text-center">
                    <span className="text-[10px] text-muted-foreground block">GPU hours</span>
                    <span className="text-lg font-bold">{telemetry?.total_gpu_hours ?? "—"}</span>
                  </div>
                  <div className="p-3 rounded bg-muted text-center">
                    <span className="text-[10px] text-muted-foreground block">Cost (USD)</span>
                    <span className="text-lg font-bold">${telemetry?.total_cost_usd ?? "—"}</span>
                  </div>
                  <div className="p-3 rounded bg-muted text-center">
                    <span className="text-[10px] text-muted-foreground block">Bench delta</span>
                    <span className="text-lg font-bold">{telemetry?.total_benchmark_delta ?? "—"}</span>
                  </div>
                  <div className="p-3 rounded bg-muted text-center">
                    <span className="text-[10px] text-muted-foreground block">$/point</span>
                    <span className="text-lg font-bold">{telemetry?.cost_per_benchmark_point ?? "—"}</span>
                  </div>
                </div>
                {telemetry && Object.keys(telemetry.per_adapter).length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold mb-2">Per adapter</h3>
                    <div className="divide-y divide-border rounded-lg border">
                      {Object.entries(telemetry.per_adapter).map(([adapter, data]) => (
                        <div key={adapter} className="flex items-center justify-between px-4 py-2.5 text-sm">
                          <span className="font-mono">{adapter}</span>
                          <span className="text-xs text-muted-foreground">
                            {data.runs} runs · {data.gpu_hours}h · ${data.cost_usd}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="alerts" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-primary" /> Alert Feed</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="divide-y divide-border rounded-lg border">
                  {alerts.map((a, i) => (
                    <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant={a.severity === "critical" ? "destructive" : a.severity === "high" ? "warning" : "secondary"}>
                          {String(a.severity)}
                        </Badge>
                        <span>{String(a.title)}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{String(a.created_at).slice(11, 19)}</span>
                    </div>
                  ))}
                  {alerts.length === 0 && <p className="px-4 py-3 text-xs text-muted-foreground">No alerts yet.</p>}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="profile" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2"><User className="w-4 h-4 text-primary" /> Personalized Learning Profile</CardTitle>
                <CardDescription className="text-xs">Learned from your interactions; biases research & benchmarks</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-3 p-3 rounded-lg bg-muted">
                  <span className="text-xs text-muted-foreground block">Dominant stack</span>
                  <span className="text-xl font-bold">{profile?.dominant_stack ?? "general"}</span>
                </div>
                <div className="space-y-2">
                  {(profile?.stacks ?? []).map(s => (
                    <div key={s.stack} className="flex items-center gap-2">
                      <span className="text-xs w-24">{s.stack}</span>
                      <div className="flex-1 h-2 rounded bg-muted overflow-hidden">
                        <div className="h-full bg-primary rounded" style={{ width: `${Math.max(2, s.share * 100)}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground w-10 text-right">{Math.round(s.share * 100)}%</span>
                    </div>
                  ))}
                  {!profile?.stacks?.length && <p className="text-xs text-muted-foreground">No signals yet — interact with the chat to build a profile.</p>}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}