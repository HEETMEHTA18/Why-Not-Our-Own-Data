const TATVIK_URL = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"
const GOVERNOR_URL = process.env.NEXT_PUBLIC_GOVERNOR_URL || "http://localhost:8100"
const HERMES_URL = process.env.NEXT_PUBLIC_HERMES_URL || "http://localhost:8101"

async function request<T>(base: string, path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`${base}${path} ${res.status}: ${res.statusText}`)
  }
  return res.json()
}

function serialize(obj?: Record<string, unknown>): string {
  if (!obj) return ""
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null) q.set(k, String(v))
  }
  return q.toString()
}

export const tatvik = {
  models: {
    list: () => request<import("./types").ModelInfo[]>(TATVIK_URL, "/models"),
    get: (name: string) => request<Record<string, unknown>>(TATVIK_URL, `/models/${encodeURIComponent(name)}`),
    pull: (name: string) => request<{ name: string }>(TATVIK_URL, `/models/pull?name=${encodeURIComponent(name)}`, { method: "POST" }),
    delete: (name: string) => request<{ name: string }>(TATVIK_URL, `/models/${encodeURIComponent(name)}`, { method: "DELETE" }),
    stats: () => request<Record<string, unknown>>(TATVIK_URL, "/models/runtime/stats"),
  },
  evaluation: {
    run: (baseModel: string, adapterPath?: string, config?: Record<string, unknown>) => {
      const q = serialize({ base_model: baseModel, adapter_path: adapterPath })
      return request<Record<string, unknown>>(TATVIK_URL, `/evaluation/run?${q}`, {
        method: "POST",
        body: config ? JSON.stringify(config) : undefined,
      })
    },
    list: (adapterId?: string) => {
      const q = adapterId ? `?adapter_id=${adapterId}` : ""
      return request<import("./types").BenchmarkResult[]>(TATVIK_URL, `/evaluation/benchmarks${q}`)
    },
    compare: (baseModel: string, adapterIds: string[]) =>
      request<Record<string, unknown[]>>(TATVIK_URL,
        `/evaluation/compare?base_model=${encodeURIComponent(baseModel)}&adapter_ids=${adapterIds.join(",")}`),
    suites: () => request<Record<string, unknown>>(TATVIK_URL, "/evaluation/suites"),
  },
  training: {
    start: (config: Record<string, unknown>) =>
      request<Record<string, unknown>>(TATVIK_URL, "/training", { method: "POST", body: JSON.stringify(config) }),
    status: () => request<Record<string, unknown>[]>(TATVIK_URL, "/training/status"),
    cancel: (jobId: string) =>
      request<{ job_id: string }>(TATVIK_URL, `/training/cancel/${jobId}`, { method: "POST" }),
    adapters: (baseModelId?: string) => {
      const q = baseModelId ? `?base_model_id=${baseModelId}` : ""
      return request<import("./types").AdapterRecord[]>(TATVIK_URL, `/training/adapters${q}`)
    },
    getAdapter: (id: string) =>
      request<import("./types").AdapterRecord>(TATVIK_URL, `/training/adapters/${id}`),
  },
  deployment: {
    deploy: (adapterId: string) =>
      request<Record<string, unknown>>(TATVIK_URL, `/deployment/deploy/${adapterId}`, { method: "POST" }),
    rollback: (adapterId: string, reason?: string) => {
      const q = reason ? `?reason=${encodeURIComponent(reason)}` : ""
      return request<Record<string, unknown>>(TATVIK_URL, `/deployment/rollback/${adapterId}${q}`, { method: "POST" })
    },
    shouldRollback: (adapterId: string) =>
      request<Record<string, unknown>>(TATVIK_URL, `/deployment/should-rollback/${adapterId}`, { method: "POST" }),
    compare: (baseModelId: string) =>
      request<Record<string, unknown>[]>(TATVIK_URL, `/deployment/compare/${baseModelId}`),
    status: (baseModelId: string) =>
      request<Record<string, unknown>>(TATVIK_URL, `/deployment/status/${baseModelId}`),
  },
  experiments: {
    list: (limit?: number) => {
      const q = limit ? `?limit=${limit}` : ""
      return request<import("./types").ExperimentRecord[]>(TATVIK_URL, `/experiments${q}`)
    },
    get: (id: string) =>
      request<import("./types").ExperimentRecord>(TATVIK_URL, `/experiments/${id}`),
  },
  registry: {
    models: () => request<Record<string, unknown>[]>(TATVIK_URL, "/registry/models"),
    getModel: (id: string) => request<Record<string, unknown>>(TATVIK_URL, `/registry/models/${id}`),
    versions: (baseModelId: string) =>
      request<Record<string, unknown>[]>(TATVIK_URL, `/registry/versions/${baseModelId}`),
  },
  system: {
    health: () => request<Record<string, unknown>>(TATVIK_URL, "/system/health"),
    gpu: () => request<import("./types").GPUInfo>(TATVIK_URL, "/system/gpu"),
    scheduler: () => request<Record<string, unknown>>(TATVIK_URL, "/system/scheduler"),
    jobs: (limit?: number) => {
      const q = limit ? `?limit=${limit}` : ""
      return request<Record<string, unknown>[]>(TATVIK_URL, `/system/scheduler/jobs${q}`)
    },
    settings: () => request<Record<string, unknown>>(TATVIK_URL, "/system/settings"),
    updateSettings: (body: Record<string, unknown>) =>
      request<Record<string, unknown>>(TATVIK_URL, "/system/settings", { method: "PUT", body: JSON.stringify(body) }),
    logs: (limit?: number) => request<Record<string, unknown>[]>(TATVIK_URL, `/system/logs${limit ? `?limit=${limit}` : ""}`),
  },
  chat: {
    generate: (body: { model: string; prompt: string; stream?: boolean; options?: Record<string, unknown> }) =>
      request<Record<string, unknown>>(TATVIK_URL, "/models/generate", { method: "POST", body: JSON.stringify(body) }),
    chat: (body: { model: string; messages: import("./types").ChatMessage[]; stream?: boolean }) =>
      request<Record<string, unknown>>(TATVIK_URL, "/models/chat", { method: "POST", body: JSON.stringify(body) }),
  },
  sahapatha: {
    status: () => request<import("./types").SahapathaStatus>(TATVIK_URL, "/sahapatha/status"),
    learn: (data: { prompt: string; response: string; metadata?: Record<string, unknown> }) =>
      request<{ interaction_id: string; status: string; buffer_size: number }>(TATVIK_URL, "/sahapatha/learn", { method: "POST", body: JSON.stringify(data) }),
    train: () => request<Record<string, unknown>>(TATVIK_URL, "/sahapatha/train", { method: "POST" }),
    adapters: () => request<import("./types").SahapathaAdapter[]>(TATVIK_URL, "/sahapatha/adapters"),
  },
}

export const governor = {
  recommend: () => request<import("./types").GovernorDecision>(GOVERNOR_URL, "/governor/recommend-training"),
  approve: (recommendationId: string, approved: boolean, notes?: string) =>
    request<import("./types").TrainingRecommendation>(GOVERNOR_URL, "/governor/approve", {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId, approved, notes: notes || "" }),
    }),
  recommendations: (status?: string) => {
    const q = status ? `?status=${status}` : ""
    return request<import("./types").TrainingRecommendation[]>(GOVERNOR_URL, `/governor/recommendations${q}`)
  },
  getRecommendation: (id: string) =>
    request<import("./types").TrainingRecommendation>(GOVERNOR_URL, `/governor/recommendation/${id}`),
  consent: {
    prompt: (recommendationId: string) =>
      request<import("./types").ConsentPrompt>(GOVERNOR_URL, `/consent/prompt/${recommendationId}`),
    respond: (recommendationId: string, decision: string, notes?: string) =>
      request<{ recorded: boolean }>(GOVERNOR_URL, "/consent/respond", {
        method: "POST",
        body: JSON.stringify({ recommendation_id: recommendationId, decision, timestamp: new Date().toISOString(), notes: notes || "" }),
      }),
  },
  quality: {
    scoreAll: () => request<{ scored: number }>(GOVERNOR_URL, "/quality/score-all", { method: "POST" }),
    report: () => request<Record<string, unknown>>(GOVERNOR_URL, "/quality/report"),
  },
  collector: {
    storeConversation: (data: Record<string, unknown>) =>
      request<Record<string, unknown>>(GOVERNOR_URL, "/collect/conversation", { method: "POST", body: JSON.stringify(data) }),
    listConversations: (params?: Record<string, unknown>) => {
      const q = serialize(params as Record<string, unknown>)
      return request<Record<string, unknown>[]>(GOVERNOR_URL, `/collect/conversations?${q}`)
    },
    stats: () => request<{ total: number; with_corrections: number; without_corrections: number }>(GOVERNOR_URL, "/collect/stats"),
  },
  dataset: {
    build: (source?: string) => {
      const q = source ? `?source=${source}` : ""
      return request<Record<string, unknown>>(GOVERNOR_URL, `/dataset/build${q}`, { method: "POST" })
    },
    examples: (validOnly?: boolean) => {
      const q = validOnly !== undefined ? `?valid_only=${validOnly}` : ""
      return request<Record<string, unknown>[]>(GOVERNOR_URL, `/dataset/examples${q}`)
    },
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/dataset/stats"),
    clean: () => request<Record<string, unknown>>(GOVERNOR_URL, "/dataset/clean", { method: "POST" }),
  },
  memory: {
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/memory/stats"),
    search: (query: string) => request<Record<string, unknown>>(GOVERNOR_URL, `/memory/kb/search?query=${encodeURIComponent(query)}`),
  },
  agents: {
    list: () => request<{ agents: import("./types").GovernorAgent[] }>(GOVERNOR_URL, "/agents/"),
    run: (agentId: string) => request<import("./types").AgentRun>(GOVERNOR_URL, `/agents/${agentId}/run`, { method: "POST" }),
    status: () => request<Record<string, unknown>>(GOVERNOR_URL, "/agents/status"),
    pipelineRun: (name: string) =>
      request<{ pipeline: string; results: Record<string, unknown>[] }>(GOVERNOR_URL, "/agents/pipeline/run", {
        method: "POST", body: JSON.stringify({ name }),
      }),
    initPipelines: () => request<Record<string, unknown>>(GOVERNOR_URL, "/agents/initialize-pipelines", { method: "POST" }),
  },
  knowledge: {
    govern: (knowledgeId: string, text: string, title: string, knowledgeType: string, confidence: number) =>
      request<import("./types").GovernorDecision>(GOVERNOR_URL, "/governor/govern", {
        method: "POST",
        body: JSON.stringify({ knowledge_id: knowledgeId, text, title, knowledge_type: knowledgeType, confidence }),
      }),
    readiness: () => request<Record<string, unknown>>(GOVERNOR_URL, "/governor/readiness"),
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/governor/stats"),
    log: () => request<{ items: import("./types").GovernorDecision[] }>(GOVERNOR_URL, "/governor/log"),
  },
  kg: {
    nodes: (type?: string) => request<{ nodes: import("./types").KGNode[]; total: number }>(GOVERNOR_URL, `/kg/${type ? `?node_type=${type}` : ""}`),
    search: (query: string) =>
      request<{ results: import("./types").KGNode[]; count: number }>(GOVERNOR_URL, `/kg/search?query=${encodeURIComponent(query)}`),
    node: (name: string) =>
      request<{ node: import("./types").KGNode; connections: import("./types").KGConnection[] }>(GOVERNOR_URL, `/kg/node/${encodeURIComponent(name)}`),
    path: (source: string, target: string) =>
      request<{ nodes: import("./types").KGNode[]; edges: import("./types").KGEdge[]; distance: number }>(
        GOVERNOR_URL, `/kg/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`),
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/kg/stats"),
  },
  benchmarks: {
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/benchmarks/stats"),
    domain: (domain: string, difficulty?: string) =>
      request<{ domain: string; total: number; tasks: import("./types").BenchmarkTask[] }>(
        GOVERNOR_URL, `/benchmarks/domain/${domain}${difficulty ? `?difficulty=${difficulty}` : ""}`),
    random: (count: number = 5, domain?: string) =>
      request<{ tasks: import("./types").BenchmarkTask[]; count: number }>(
        GOVERNOR_URL, `/benchmarks/random?count=${count}${domain ? `&domain=${domain}` : ""}`),
    search: (q: string) => request<Record<string, unknown>>(GOVERNOR_URL, `/benchmarks/search?q=${encodeURIComponent(q)}`),
  },
  scheduler: {
    jobs: () => request<{ jobs: import("./types").SchedulerJob[] }>(GOVERNOR_URL, "/scheduler/jobs"),
    initDefaults: () => request<Record<string, unknown>>(GOVERNOR_URL, "/scheduler/jobs/init-defaults", { method: "POST" }),
    toggle: (jobId: string, enabled: boolean) =>
      request<Record<string, unknown>>(GOVERNOR_URL, `/scheduler/jobs/${jobId}/toggle?enabled=${enabled}`, { method: "POST" }),
    logs: () => request<{ logs: Record<string, unknown>[] }>(GOVERNOR_URL, "/scheduler/logs"),
  },
  events: {
    stats: () => request<import("./types").EventBusStats>(GOVERNOR_URL, "/events/stats"),
    recent: (limit?: number) => request<Record<string, unknown>[]>(GOVERNOR_URL, `/events/recent${limit ? `?limit=${limit}` : ""}`),
  },
}

export const hermes = {
  health: () => request<Record<string, unknown>>(HERMES_URL, "/health"),
  status: () => request<import("./types").HermesStatus>(HERMES_URL, "/status"),
  agents: {
    list: () => request<{ agents: import("./types").HermesAgent[] }>(HERMES_URL, "/agents"),
    run: (agentId: string) => request<import("./types").HermesRun>(HERMES_URL, "/agents/run", {
      method: "POST", body: JSON.stringify({ agent_id: agentId }),
    }),
    runAll: () => request<{ results: import("./types").HermesRun[] }>(HERMES_URL, "/agents/run-all", { method: "POST" }),
  },
  pipelines: {
    list: () => request<{ pipelines: string[] }>(HERMES_URL, "/pipelines"),
    run: (name: string) => request<import("./types").HermesPipelineRun>(HERMES_URL, "/pipelines/run", {
      method: "POST", body: JSON.stringify({ pipeline_name: name }),
    }),
  },
  runs: (agentId?: string, limit?: number) => {
    const params = new URLSearchParams()
    if (agentId) params.set("agent_id", agentId)
    if (limit) params.set("limit", String(limit))
    const q = params.toString()
    return request<{ runs: Record<string, unknown>[] }>(HERMES_URL, `/runs${q ? `?${q}` : ""}`)
  },
  events: {
    stats: () => request<{ stats: import("./types").EventBusStats }>(HERMES_URL, "/events/stats"),
    recent: (limit?: number) => request<{ events: Record<string, unknown>[] }>(HERMES_URL, `/events/recent${limit ? `?limit=${limit}` : ""}`),
  },
}

export const platform = {
  consensus: {
    decide: (body: { knowledge_id: string; text: string; title?: string; knowledge_type?: string; confidence?: number }) =>
      request<import("./types").ConsensusDecision>(GOVERNOR_URL, "/platform/consensus/decide", { method: "POST", body: JSON.stringify(body) }),
    members: () => request<{ members: string[] }>(GOVERNOR_URL, "/platform/consensus/members"),
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/platform/consensus/stats"),
    recent: (limit?: number) => request<{ decisions: Record<string, unknown>[] }>(GOVERNOR_URL, `/platform/consensus/recent?limit=${limit ?? 50}`),
  },
  feedback: {
    regression: (task: string, deltaScore: number, knowledgeType?: string) =>
      request<{ adjusted: number; adjustments: import("./types").TuningAdjustment[]; reason: string }>(
        GOVERNOR_URL, "/platform/feedback/regression", { method: "POST", body: JSON.stringify({ task, delta_score: deltaScore, knowledge_type: knowledgeType || "" }) }),
    thresholds: () => request<{ thresholds: Record<string, Record<string, number>> }>(GOVERNOR_URL, "/platform/feedback/thresholds"),
    history: () => request<{ tuning: Record<string, unknown>[] }>(GOVERNOR_URL, "/platform/feedback/history"),
    reset: () => request<{ reset: number }>(GOVERNOR_URL, "/platform/feedback/reset", { method: "POST" }),
  },
  routing: {
    route: (prompt: string) => request<import("./types").RouteResult>(GOVERNOR_URL, "/platform/routing/route", { method: "POST", body: JSON.stringify({ prompt }) }),
    register: (adapterId: string, domain: string, benchmarkScore: number, baselineScore: number) =>
      request<{ registered: boolean }>(GOVERNOR_URL, "/platform/routing/register", { method: "POST", body: JSON.stringify({ adapter_id: adapterId, domain, benchmark_score: benchmarkScore, baseline_score: baselineScore }) }),
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/platform/routing/stats"),
    adapters: () => request<{ adapters: Record<string, unknown>[] }>(GOVERNOR_URL, "/platform/routing/adapters"),
  },
  lineage: {
    link: (sourceType: string, sourceId: string, targetType: string, targetId: string, linkType?: string) =>
      request<{ link_id: string }>(GOVERNOR_URL, "/platform/lineage/link", { method: "POST", body: JSON.stringify({ source_type: sourceType, source_id: sourceId, target_type: targetType, target_id: targetId, link_type: linkType || "derived_from" }) }),
    trace: (targetType: string, targetId: string) =>
      request<{ target: { type: string; id: string }; chain: { type: string; id: string; depth: number }[]; length: number }>(
        GOVERNOR_URL, `/platform/lineage/trace?target_type=${targetType}&target_id=${targetId}`),
  },
  telemetry: {
    record: (body: { adapter_id?: string; task?: string; gpu_hours?: number; gpu_type?: string; benchmark_delta?: number }) =>
      request<{ run_id: string }>(GOVERNOR_URL, "/platform/telemetry/record", { method: "POST", body: JSON.stringify(body) }),
    stats: () => request<import("./types").TelemetryStats>(GOVERNOR_URL, "/platform/telemetry/stats"),
    history: () => request<{ runs: Record<string, unknown>[] }>(GOVERNOR_URL, "/platform/telemetry/history"),
  },
  alerts: {
    notify: (body: { severity?: string; title: string; message?: string; event_type?: string; payload?: Record<string, unknown> }) =>
      request<{ alert_id: string }>(GOVERNOR_URL, "/platform/alerts/notify", { method: "POST", body: JSON.stringify(body) }),
    list: () => request<{ alerts: Record<string, unknown>[] }>(GOVERNOR_URL, "/platform/alerts"),
  },
  profiler: {
    observe: (text: string, weight?: number) =>
      request<{ observed: boolean }>(GOVERNOR_URL, "/platform/profiler/observe", { method: "POST", body: JSON.stringify({ text, weight: weight || 1.0 }) }),
    profile: () => request<import("./types").ProfileResult>(GOVERNOR_URL, "/platform/profiler/profile"),
  },
  rag: {
    add: (body: { knowledge_id: string; title?: string; content: string; knowledge_type?: string; source?: string }) =>
      request<{ doc_id: string }>(GOVERNOR_URL, "/rag/add", { method: "POST", body: JSON.stringify(body) }),
    retrieve: (query: string, k?: number) =>
      request<{ context: string; documents: Record<string, unknown>[]; count: number }>(GOVERNOR_URL, "/rag/retrieve", { method: "POST", body: JSON.stringify({ query, k: k || 5 }) }),
    stats: () => request<Record<string, unknown>>(GOVERNOR_URL, "/rag/stats"),
  },
  kg: {
    ingest: (body: { text: string; title?: string; knowledge_type?: string; source?: string }) =>
      request<{ nodes_created: number; edges_created: number }>(GOVERNOR_URL, "/kg/ingest", { method: "POST", body: JSON.stringify(body) }),
    communities: () => request<{ communities: { label: string; size: number; types: Record<string, number> }[] }>(GOVERNOR_URL, "/kg/communities"),
    emerging: () => request<{ topics: Record<string, unknown>[] }>(GOVERNOR_URL, "/kg/emerging"),
  },
}
