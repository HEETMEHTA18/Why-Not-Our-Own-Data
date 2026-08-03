"use client"

import { AppShell } from "@/components/layout/app-shell"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { hermes } from "@/lib/api"
import type { HermesStatus, HermesRun, EventBusStats } from "@/lib/types"
import { Play, RefreshCw, Activity, GitBranch, Cpu, Boxes, Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react"

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-gray-500",
  running: "bg-blue-500 animate-pulse",
  completed: "bg-green-500",
  failed: "bg-red-500",
  blocked: "bg-yellow-500",
}

export default function HermesPage() {
  const [status, setStatus] = useState<HermesStatus | null>(null)
  const [runs, setRuns] = useState<Record<string, unknown>[]>([])
  const [events, setEvents] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(true)
  const [runningAgent, setRunningAgent] = useState<string | null>(null)
  const [runningPipeline, setRunningPipeline] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const [s, r, e] = await Promise.all([
        hermes.status(),
        hermes.runs(undefined, 15),
        hermes.events.recent(10),
      ])
      setStatus(s)
      setRuns(r.runs)
      setEvents(e.events)
    } catch (err) {
      console.error("Failed to fetch Hermes data", err)
    }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const runAgent = async (agentId: string) => {
    setRunningAgent(agentId)
    try {
      const result = await hermes.agents.run(agentId)
      setRuns(prev => [result as unknown as Record<string, unknown>, ...prev])
    } catch (err) {
      console.error("Failed to run agent", err)
    }
    setRunningAgent(null)
    fetchData()
  }

  const runPipeline = async (name: string) => {
    setRunningPipeline(name)
    try {
      const result = await hermes.pipelines.run(name)
      setRuns(prev => [result as unknown as Record<string, unknown>, ...prev])
    } catch (err) {
      console.error("Pipeline failed", err)
    }
    setRunningPipeline(null)
    fetchData()
  }

  useEffect(() => {
    const interval = setInterval(() => { fetchData() }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Hermes Orchestrator</h1>
            <p className="text-sm text-muted-foreground">
              Autonomous multi-agent pipeline for research → dataset → training → deploy
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="w-3.5 h-3.5 mr-2" />
            Refresh
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Agents</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Boxes className="w-4 h-4 text-primary" />
                {status?.agents.length ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Pipelines</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-primary" />
                {status?.pipelines.length ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Events Processed</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" />
                {status?.event_bus.total_events ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>System</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary" />
                <Badge variant={status?.status === "ready" ? "default" : "secondary"}>
                  {status?.status ?? "offline"}
                </Badge>
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        <Tabs defaultValue="agents">
          <TabsList>
            <TabsTrigger value="agents">Agents</TabsTrigger>
            <TabsTrigger value="pipelines">Pipelines</TabsTrigger>
            <TabsTrigger value="runs">Run History</TabsTrigger>
            <TabsTrigger value="events">Events</TabsTrigger>
          </TabsList>

          <TabsContent value="agents" className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {status?.agents.map((agent) => (
                <Card key={agent.id}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[agent.status] ?? "bg-gray-500"}`} />
                      <div>
                        <p className="text-sm font-medium">{agent.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">{agent.id} · {agent.type}</p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={runningAgent === agent.id || agent.status === "running"}
                      onClick={() => runAgent(agent.id)}
                    >
                      {runningAgent === agent.id ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                      <span className="ml-1.5">Run</span>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="pipelines" className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {status?.pipelines.map((p) => (
                <Card key={p}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <GitBranch className="w-4 h-4 text-primary" />
                      <p className="text-sm font-medium">{p}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={runningPipeline === p}
                      onClick={() => runPipeline(p)}
                    >
                      {runningPipeline === p ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                      <span className="ml-1.5">Run</span>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="runs" className="mt-4">
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="h-[400px]">
                  <div className="divide-y divide-border">
                    {runs.map((run, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-3">
                        <div className="flex items-center gap-3">
                          {run.status === "completed" ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : run.status === "failed" ? (
                            <XCircle className="w-4 h-4 text-red-500" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-yellow-500" />
                          )}
                          <div>
                            <p className="text-sm font-medium">
                              {(run.agent_id as string) || (run.pipeline as string) || "run"}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {String(run.run_id ?? "").slice(0, 12)} · {String(run.started_at ?? "").slice(11, 19)}
                            </p>
                          </div>
                        </div>
                        <Badge variant={run.status === "completed" ? "default" : run.status === "failed" ? "destructive" : "secondary"}>
                          {String(run.status)}
                        </Badge>
                      </div>
                    ))}
                    {runs.length === 0 && (
                      <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
                        <Clock className="w-4 h-4 mr-2" /> No runs yet — run an agent or pipeline
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="events" className="mt-4">
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="h-[400px]">
                  <div className="divide-y divide-border">
                    {events.map((ev, i) => (
                      <div key={i} className="px-4 py-2.5">
                        <p className="text-sm font-mono">{String(ev.type ?? "event")}</p>
                        <p className="text-xs text-muted-foreground">
                          {String(ev.timestamp ?? ev.published_at ?? "")} · {String(ev.source_id ?? "")}
                        </p>
                      </div>
                    ))}
                    {events.length === 0 && (
                      <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
                        <Activity className="w-4 h-4 mr-2" /> No events published yet
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}