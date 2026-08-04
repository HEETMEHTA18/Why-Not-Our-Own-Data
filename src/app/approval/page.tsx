"use client"

import { AppShell } from "@/components/layout/app-shell"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { governor, platform } from "@/lib/api"
import type { ConsensusDecision, TrainingRecommendation } from "@/lib/types"
import { CheckCircle, XCircle, Shield, GitFork, TrendingUp, Users } from "lucide-react"

const ACTION_COLORS: Record<string, string> = {
  ignore: "bg-gray-100 text-gray-600",
  store_rag: "bg-blue-100 text-blue-600",
  store_kg: "bg-green-100 text-green-600",
  recommend_lora: "bg-purple-100 text-purple-600",
}

export default function ApprovalPage() {
  const [recommendations, setRecommendations] = useState<TrainingRecommendation[]>([])
  const [councilDecisions, setCouncilDecisions] = useState<ConsensusDecision[]>([])
  const [thresholds, setThresholds] = useState<Record<string, Record<string, number>> | null>(null)
  const [decisionText, setDecisionText] = useState("")
  const [decisionTitle, setDecisionTitle] = useState("")
  const [decisionType, setDecisionType] = useState("general")
  const [decisionConf, setDecisionConf] = useState(0.7)
  const [lastConsensus, setLastConsensus] = useState<ConsensusDecision | null>(null)
  const [tuningHistory, setTuningHistory] = useState<Record<string, unknown>[]>([])

  const fetchData = async () => {
    try {
      const [recs, recent, thr, hist] = await Promise.all([
        governor.recommendations(),
        platform.consensus.recent(10),
        platform.feedback.thresholds(),
        platform.feedback.history().catch(() => ({ tuning: [] })),
      ])
      setRecommendations(recs)
      setCouncilDecisions(recent.decisions as unknown as ConsensusDecision[])
      setThresholds(thr.thresholds)
      setTuningHistory(hist.tuning)
    } catch (e) {
      console.error("Failed to fetch approval data", e)
    }
  }

  useEffect(() => { fetchData() }, [])

  const approve = async (id: string, approved: boolean) => {
    try {
      await governor.approve(id, approved, approved ? "approved from dashboard" : "rejected from dashboard")
      fetchData()
    } catch (e) {
      console.error("Approval failed", e)
    }
  }

  const runConsensus = async () => {
    if (!decisionText) return
    try {
      const result = await platform.consensus.decide({
        knowledge_id: `review-${Date.now()}`,
        text: decisionText,
        title: decisionTitle,
        knowledge_type: decisionType,
        confidence: decisionConf,
      })
      setLastConsensus(result)
      fetchData()
    } catch (e) {
      console.error("Consensus failed", e)
    }
  }

  const pendingRecs = recommendations.filter(r => r.status === "pending")
  const approvedRecs = recommendations.filter(r => r.status === "approved")

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Approval Queue</h1>
            <p className="text-sm text-muted-foreground">
              Review training recommendations and council governance decisions
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData}>Refresh</Button>
        </div>

        <Tabs defaultValue="recommendations">
          <TabsList>
            <TabsTrigger value="recommendations">Training Recommendations</TabsTrigger>
            <TabsTrigger value="council">Council Decisions</TabsTrigger>
            <TabsTrigger value="governance">Self-Tuning Governor</TabsTrigger>
          </TabsList>

          <TabsContent value="recommendations" className="mt-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {pendingRecs.map(rec => (
                <Card key={rec.id as string}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-primary" />
                        Training Recommendation
                      </CardTitle>
                      <Badge variant="warning">pending</Badge>
                    </div>
                    <CardDescription className="text-xs">
                      {String(rec.recommended_at ?? "").slice(0, 19)} · {rec.example_count} examples
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2 rounded bg-muted">
                        <span className="text-muted-foreground block">Est. improvement</span>
                        <span className="font-semibold">{String(rec.estimated_improvement ?? "—")}%</span>
                      </div>
                      <div className="p-2 rounded bg-muted">
                        <span className="text-muted-foreground block">Avg quality</span>
                        <span className="font-semibold">{String(rec.avg_quality ?? "—")}</span>
                      </div>
                      <div className="p-2 rounded bg-muted">
                        <span className="text-muted-foreground block">Duration</span>
                        <span className="font-semibold">{String(rec.estimated_duration_min ?? "—")} min</span>
                      </div>
                      <div className="p-2 rounded bg-muted">
                        <span className="text-muted-foreground block">Contradictions</span>
                        <span className="font-semibold">{String(rec.contradiction_count ?? "0")}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-1">
                      <Button size="sm" className="flex-1" onClick={() => approve(rec.id as string, true)}>
                        <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Approve
                      </Button>
                      <Button size="sm" variant="outline" className="flex-1" onClick={() => approve(rec.id as string, false)}>
                        <XCircle className="w-3.5 h-3.5 mr-1.5" /> Reject
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {pendingRecs.length === 0 && (
                <div className="col-span-2 flex items-center justify-center h-24 text-sm text-muted-foreground">
                  No pending recommendations — the governor is idle
                </div>
              )}
            </div>

            {approvedRecs.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold mb-2">Recently approved</h2>
                <div className="divide-y divide-border rounded-lg border">
                  {approvedRecs.map(rec => (
                    <div key={rec.id as string} className="flex items-center justify-between px-4 py-2.5 text-sm">
                      <span className="text-muted-foreground">#{String(rec.id).slice(0, 8)}</span>
                      <Badge variant="success">approved</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="council" className="mt-4 space-y-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Users className="w-4 h-4 text-primary" /> Run Council Decision
                </CardTitle>
                <CardDescription className="text-xs">
                  Research, Documentation, Dataset and Quality agents vote on an item
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Input placeholder="Knowledge text" value={decisionText} onChange={e => setDecisionText(e.target.value)} />
                <div className="grid grid-cols-3 gap-2">
                  <Input placeholder="Title" value={decisionTitle} onChange={e => setDecisionTitle(e.target.value)} />
                  <Input placeholder="Type" value={decisionType} onChange={e => setDecisionType(e.target.value)} />
                  <Input type="number" min={0} max={1} step={0.05} value={decisionConf} onChange={e => setDecisionConf(Number(e.target.value))} />
                </div>
                <Button onClick={runConsensus} disabled={!decisionText}>
                  <Shield className="w-3.5 h-3.5 mr-1.5" /> Decide
                </Button>
              </CardContent>
            </Card>

            {lastConsensus && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Latest decision — {lastConsensus.action}</CardTitle>
                  <CardDescription className="text-xs">
                    consensus {lastConsensus.consensus} · disagreement {lastConsensus.disagreement} · {lastConsensus.knowledge_id}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {lastConsensus.votes.map(v => (
                      <div key={v.member} className="flex items-center justify-between p-2 rounded bg-muted text-xs">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{v.member}</Badge>
                          <span>{v.reasoning}</span>
                        </div>
                        <span className="font-mono">
                          {v.preferred_action} · conf {v.confidence} · risk {v.risk}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="divide-y divide-border rounded-lg border">
              {councilDecisions.map((d, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge className={ACTION_COLORS[d.action] || ""}>{d.action}</Badge>
                    <span className="text-muted-foreground font-mono text-xs">{d.knowledge_id}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    consensus {d.consensus} · {d.decided_at.slice(11, 19)}
                  </span>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="governance" className="mt-4 space-y-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-primary" /> Current Governor Thresholds
                </CardTitle>
                <CardDescription className="text-xs">
                  The governor auto-tunes these when benchmarks regress
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {thresholds && Object.entries(thresholds).map(([policy, params]) => (
                    <div key={policy} className="p-3 rounded border">
                      <p className="text-xs font-semibold mb-1">{policy}</p>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(params).map(([k, v]) => (
                          <Badge key={k} variant="outline" className="text-[10px] font-mono">
                            {k}={v}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <Button size="sm" variant="outline" className="mt-3" onClick={async () => { await platform.feedback.reset(); fetchData(); }}>
                  Reset thresholds to defaults
                </Button>
              </CardContent>
            </Card>
            <ScrollArea className="h-[300px]">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">Tuning history</h3>
                {tuningHistory.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No tuning events recorded yet.</p>
                ) : tuningHistory.map((h, i) => (
                  <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm border rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {String(h.policy ?? "—")} · {String(h.parameter ?? "—")}: {String(h.before_value ?? "—")} → {String(h.after_value ?? "—")}
                        {" "}{String(h.direction ?? "")}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">
                      {h.tuned_at ? String(h.tuned_at).slice(0, 19) : ""}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}