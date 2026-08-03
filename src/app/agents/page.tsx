"use client"

import { AppShell } from "@/components/layout/app-shell"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { governor } from "@/lib/api"
import type { GovernorAgent, AgentRun, PipelineDefinition, EventBusStats } from "@/lib/types"
import { Play, RefreshCw, Activity, GitBranch, Zap, Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react"

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-gray-500",
  running: "bg-blue-500 animate-pulse",
  completed: "bg-green-500",
  failed: "bg-red-500",
  blocked: "bg-yellow-500",
}

const STATUS_ICONS: Record<string, typeof Activity> = {
  idle: Activity,
  running: RefreshCw,
  completed: CheckCircle,
  failed: XCircle,
  blocked: AlertCircle,
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<GovernorAgent[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([])
  const [eventStats, setEventStats] = useState<EventBusStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [runningAgent, setRunningAgent] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const [a, s] = await Promise.all([
        governor.agents.list(),
        governor.events.stats(),
      ])
      setAgents(a.agents)
      setEventStats(s)
    } catch (e) {
      console.error("Failed to fetch agent data", e)
    }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const runAgent = async (agentId: string) => {
    setRunningAgent(agentId)
    try {
      const result = await governor.agents.run(agentId)
      setRuns(prev => [result as unknown as AgentRun, ...prev])
    } catch (e) {
      console.error("Failed to run agent", e)
    }
    setRunningAgent(null)
  }

  const runPipeline = async (name: string) => {
    try {
      const result = await governor.agents.pipelineRun(name)
    } catch (e) {
      console.error("Pipeline failed", e)
    }
  }

  const initPipelines = async () => {
    try {
      await governor.agents.initPipelines()
      fetchData()
    } catch (e) {
      console.error("Init failed", e)
    }
  }

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Agent Orchestrator</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Multi-agent system for autonomous knowledge extraction, training, and deployment
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={initPipelines}>
              <GitBranch className="w-4 h-4 mr-2" />
              Init Pipelines
            </Button>
            <Button variant="outline" onClick={fetchData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {eventStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-sm">Events Processed</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{eventStats.total_events}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-sm">Subscriptions</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{eventStats.active_subscriptions}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-sm">Queue Depth</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{eventStats.queue_depth}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-sm">Failed Events</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold text-red-500">{eventStats.failed_events}</p></CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="agents">
          <TabsList>
            <TabsTrigger value="agents"><Zap className="w-4 h-4 mr-2" />Agents</TabsTrigger>
            <TabsTrigger value="pipelines"><GitBranch className="w-4 h-4 mr-2" />Pipelines</TabsTrigger>
            <TabsTrigger value="runs"><Clock className="w-4 h-4 mr-2" />Run History</TabsTrigger>
          </TabsList>

          <TabsContent value="agents" className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map(agent => {
                const StatusIcon = STATUS_ICONS[agent.status] || Activity
                return (
                  <Card key={agent.agent_id}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[agent.status] || "bg-gray-500"}`} />
                          <CardTitle className="text-base">{agent.name}</CardTitle>
                        </div>
                        <Badge variant="outline">{agent.agent_type}</Badge>
                      </div>
                      <CardDescription>{agent.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          Status: <span className="font-medium capitalize">{agent.status}</span>
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => runAgent(agent.agent_id)}
                          disabled={runningAgent === agent.agent_id}
                        >
                          <Play className="w-3 h-3 mr-1" />
                          {runningAgent === agent.agent_id ? "Running..." : "Run"}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </TabsContent>

          <TabsContent value="pipelines" className="mt-4">
            <div className="space-y-4">
              {pipelines.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No pipelines defined. Click "Init Pipelines" to create the default set.
                  </CardContent>
                </Card>
              ) : pipelines.map(p => (
                <Card key={p.name}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{p.name}</CardTitle>
                      <Button size="sm" onClick={() => runPipeline(p.name)}>
                        <Play className="w-3 h-3 mr-1" /> Run
                      </Button>
                    </div>
                    <CardDescription>{p.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {p.steps.map((s, i) => (
                        <Badge key={i} variant="secondary">
                          {i + 1}. {s.agent_id}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="runs" className="mt-4">
            <ScrollArea className="h-[500px]">
              {runs.length === 0 ? (
                <Card><CardContent className="py-8 text-center text-muted-foreground">No runs yet. Run an agent to see history.</CardContent></Card>
              ) : runs.map(run => (
                <Card key={run.run_id} className="mb-2">
                  <CardContent className="py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[run.status] || "bg-gray-500"}`} />
                        <span className="text-sm font-medium">{run.agent_id}</span>
                        <Badge variant="outline" className="text-xs">{run.status}</Badge>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {run.started_at ? new Date(run.started_at).toLocaleString() : ""}
                      </span>
                    </div>
                    {run.result && Object.keys(run.result).length > 0 && (
                      <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-x-auto">
                        {JSON.stringify(run.result, null, 2).slice(0, 300)}
                      </pre>
                    )}
                    {run.error && (
                      <p className="mt-1 text-xs text-red-500">{run.error}</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}