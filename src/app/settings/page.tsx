"use client"

import { useEffect, useState, useCallback } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Settings, Cpu, Bell, Database, FlaskConical } from "lucide-react"
import { tatvik } from "@/lib/api"

interface SettingsData {
  default_model: string
  context_length: number
  temperature: number
  max_tokens: number
  lora_rank: number
  learning_rate: number
  epochs: number
  min_dataset_size: number
  training_ready: boolean
  benchmark_complete: boolean
  gpu_temp_warning: boolean
  error_alerts: boolean
  dataset_retention_days: number
  log_retention_days: number
  auto_cleanup: boolean
}

const DEFAULTS: SettingsData = {
  default_model: "qwen2.5-coder-3b-instruct",
  context_length: 4096,
  temperature: 0.7,
  max_tokens: 2048,
  lora_rank: 16,
  learning_rate: 0.0002,
  epochs: 3,
  min_dataset_size: 50,
  training_ready: true,
  benchmark_complete: true,
  gpu_temp_warning: true,
  error_alerts: true,
  dataset_retention_days: 10,
  log_retention_days: 30,
  auto_cleanup: true,
}

export default function SettingsPage() {
  const [values, setValues] = useState<SettingsData>(DEFAULTS)
  const [models, setModels] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [notice, setNotice] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [settings, modelList] = await Promise.all([
        tatvik.system.settings(),
        tatvik.models.list().catch(() => []),
      ])
      const keys = Object.keys(DEFAULTS) as (keyof SettingsData)[]
      const next = { ...DEFAULTS }
      for (const key of keys) {
        const v = settings[key]
        if (v !== undefined && v !== null) next[key] = v as never
      }
      setValues(next)
      setModels((modelList as { name?: string }[]).map((m) => m.name ?? "").filter(Boolean))
      setDirty(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const set = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    setValues((v) => ({ ...v, [key]: value }))
    setDirty(true)
  }

  const save = async () => {
    setSaving(true)
    setNotice("")
    try {
      await tatvik.system.updateSettings({
        default_model: values.default_model,
        lora_rank: values.lora_rank,
        learning_rate: values.learning_rate,
        epochs: values.epochs,
      })
      setDirty(false)
      setNotice("Settings saved")
      setTimeout(() => setNotice(""), 3000)
    } catch (err) {
      setNotice(`Failed to save: ${err instanceof Error ? err.message : "unknown error"}`)
    } finally {
      setSaving(false)
    }
  }

  const sections = [
    {
      title: "Model Settings",
      icon: Cpu,
      fields: [
        { label: "Default Model", value: values.default_model, type: "select", options: models },
        { label: "Context Length", value: String(values.context_length), type: "number", key: "context_length" },
        { label: "Temperature", value: String(values.temperature), type: "number", key: "temperature" },
        { label: "Max Tokens", value: String(values.max_tokens), type: "number", key: "max_tokens" },
      ] as const,
    },
    {
      title: "Training Settings",
      icon: FlaskConical,
      fields: [
        { label: "LoRA Rank (r)", value: String(values.lora_rank), type: "number", key: "lora_rank" },
        { label: "Learning Rate", value: String(values.learning_rate), type: "number", key: "learning_rate" },
        { label: "Epochs", value: String(values.epochs), type: "number", key: "epochs" },
        { label: "Min Dataset Size", value: String(values.min_dataset_size), type: "number", key: "min_dataset_size" },
      ] as const,
    },
    {
      title: "Notifications",
      icon: Bell,
      fields: [
        { label: "Training Ready", key: "training_ready", type: "toggle" },
        { label: "Benchmark Complete", key: "benchmark_complete", type: "toggle" },
        { label: "GPU Temperature Warning", key: "gpu_temp_warning", type: "toggle" },
        { label: "Error Alerts", key: "error_alerts", type: "toggle" },
      ] as const,
    },
    {
      title: "Storage",
      icon: Database,
      fields: [
        { label: "Dataset Retention", key: "dataset_retention_days", type: "number" },
        { label: "Log Retention", key: "log_retention_days", type: "number" },
        { label: "Auto-cleanup", key: "auto_cleanup", type: "toggle" },
      ] as const,
    },
  ] as const

  return (
    <AppShell>
      <div className="space-y-8 max-w-3xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            Settings
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Configure your platform</p>
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading settings…</p>}

        {sections.map((section) => {
          const Icon = section.icon
          return (
            <Card key={section.title}>
              <CardHeader className="pb-4">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Icon className="w-4 h-4 text-primary" />
                  {section.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {section.fields.map((field, i) => (
                  <div key={field.label}>
                    <div className="flex items-center justify-between py-1">
                      <label className="text-sm">{field.label}</label>
                      <div className="flex items-center gap-2">
                        {field.type === "toggle" ? (
                          <button
                            type="button"
                            onClick={() => set(field.key as keyof SettingsData, !(values[field.key as keyof SettingsData] as boolean))}
                            className={`w-9 h-5 rounded-full cursor-pointer relative transition-colors ${values[field.key as keyof SettingsData] ? "bg-primary" : "bg-muted"}`}
                            aria-label={field.label}
                          >
                            <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 shadow transition-all ${values[field.key as keyof SettingsData] ? "right-0.5" : "left-0.5"}`} />
                          </button>
                        ) : field.type === "select" && "options" in field ? (
                          <select
                            className="text-sm font-mono bg-secondary px-2.5 py-1 rounded-md border-0"
                            value={String(field.value)}
                            onChange={(e) => set("default_model", e.target.value)}
                          >
                            {field.options.length > 0 ? field.options.map((m) => (
                              <option key={m} value={m}>{m}</option>
                            )) : <option value={String(field.value)}>{field.value}</option>}
                          </select>
                        ) : (
                          <input
                            type="number"
                            className="text-sm font-mono bg-secondary px-2.5 py-1 rounded-md border-0 w-28 text-right"
                            value={String(field.type === "number" ? values[field.key as keyof SettingsData] : (field as { value: string }).value)}
                            onChange={(e) => {
                              const key = field.key as keyof SettingsData
                              const num = Number(e.target.value)
                              if (key === "learning_rate") {
                                set(key, e.target.value === "" ? 0 : num)
                              } else if (["lora_rank", "epochs", "min_dataset_size", "dataset_retention_days", "log_retention_days", "context_length", "max_tokens"].includes(String(key))) {
                                set(key, e.target.value === "" ? 0 : Math.max(0, Math.floor(num)))
                              } else {
                                set(key, num)
                              }
                            }}
                          />
                        )}
                      </div>
                    </div>
                    {i < section.fields.length - 1 && <Separator className="mt-3" />}
                  </div>
                ))}
              </CardContent>
            </Card>
          )
        })}

        {notice && <p className={`text-sm ${notice.startsWith("Failed") ? "text-red-500" : "text-emerald-500"}`}>{notice}</p>}

        <div className="flex justify-end gap-3 pb-8">
          <Button variant="outline" onClick={() => { setValues(DEFAULTS); setDirty(true) }}>
            Reset to Defaults
          </Button>
          <Button onClick={save} disabled={saving || !dirty}>
            {saving ? "Saving…" : "Save Changes"}
          </Button>
        </div>
      </div>
    </AppShell>
  )
}
