"use client"

import { AppShell } from "@/components/layout/app-shell"
import { ModelCard } from "@/components/models/model-card"
import { AdapterList } from "@/components/models/adapter-list"
import { Brain, Plus, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useCallback } from "react"
import { useModels } from "@/hooks/use-models"
import { tatvik } from "@/lib/api"

export default function ModelsPage() {
  const { models, adapters, isLoading, refetch } = useModels()
  const [pulling, setPulling] = useState(false)
  const [pullingName, setPullingName] = useState("")
  const [deleting, setDeleting] = useState<string | null>(null)
  const [notice, setNotice] = useState("")

  const modelCards = models.length > 0
    ? models.map((m) => ({
        id: m.name,
        name: m.model,
        provider: m.details?.family as string || "Ollama",
        size: m.size,
        quantization: m.details?.quantization_level as string || "—",
        parameterCount: m.details?.parameter_size as string || "—",
        isLoaded: true,
      }))
    : []

  const adapterRows = adapters.length > 0
    ? adapters.map((a) => ({
        id: a.id,
        version: `v${a.version}`,
        baseModelId: a.base_model_id,
        createdAt: a.created_at,
        size: 0,
        metrics: a.metrics?.accuracy || a.metrics?.eval_score
          ? { accuracy: (a.metrics.accuracy as number) || 0, latency: (a.metrics.latency as number) || 0, evalScore: (a.metrics.eval_score as number) || 0 }
          : null,
        status: (a.status === "completed" ? "active" : a.status === "failed" ? "failed" : "archived") as "active" | "archived" | "failed",
      }))
    : []

  const pullModel = useCallback(async () => {
    const name = prompt("Model name to pull (e.g. llama3.2:1b):", "qwen2.5:1.5b")
    if (!name) return
    setPulling(true)
    setPullingName(name)
    setNotice("")
    try {
      await tatvik.models.pull(name.trim())
      setNotice(`Pulled ${name.trim()}`)
      setTimeout(() => { refetch(); setNotice("") }, 2000)
    } catch (err) {
      setNotice(`Failed to pull ${name.trim()}: ${err instanceof Error ? err.message : "error"}`)
    } finally {
      setPulling(false)
    }
  }, [refetch])

  const deleteModel = useCallback(async (name: string) => {
    if (!window.confirm(`Delete model "${name}"?`)) return
    setDeleting(name)
    setNotice("")
    try {
      await tatvik.models.delete(name)
      setNotice(`Deleted ${name}`)
      setTimeout(() => { refetch(); setNotice("") }, 2000)
    } catch (err) {
      setNotice(`Failed to delete ${name}: ${err instanceof Error ? err.message : "error"}`)
    } finally {
      setDeleting(null)
    }
  }, [refetch])

  return (
    <AppShell>
      <div className="space-y-8 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Models</h1>
            <p className="text-sm text-muted-foreground mt-1">Manage base models and adapters</p>
          </div>
          <Button variant="outline" className="gap-2" onClick={pullModel} disabled={pulling}>
            {pulling ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {pulling ? `Pulling ${pullingName}…` : "Pull Model"}
          </Button>
        </div>

        {notice && <p className={`text-sm ${notice.startsWith("Failed") ? "text-red-500" : "text-emerald-500"}`}>{notice}</p>}

        <div className="space-y-4">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Base Models</h2>
          {modelCards.length === 0 && isLoading && (
            <p className="text-sm text-muted-foreground">Loading models...</p>
          )}
          {modelCards.length === 0 && !isLoading && (
            <p className="text-sm text-muted-foreground">No models found. Pull one from Ollama.</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {modelCards.map((model) => (
              <ModelCard key={model.id} model={model} onDelete={deleteModel} busy={deleting === model.id} />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Adapter Versions</h2>
          {adapterRows.length === 0 && !isLoading && (
            <p className="text-sm text-muted-foreground">No adapters yet. Train one to see it here.</p>
          )}
          {adapterRows.map((a) => (
            <AdapterList key={a.id} adapters={[a]} baseModel={a.baseModelId} />
          ))}
        </div>
      </div>
    </AppShell>
  )
}
