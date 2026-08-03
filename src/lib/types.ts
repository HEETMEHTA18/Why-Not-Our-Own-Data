export interface ModelInfo {
  name: string
  model: string
  size: number
  digest: string
  modified_at: string
  details: Record<string, unknown>
}

export interface ChatMessage {
  role: "user" | "assistant" | "system"
  content: string
  images?: string[]
}

export interface AdapterRecord {
  id: string
  base_model_id: string
  version: number
  name: string
  path: string
  dataset_id: string
  dataset_hash: string
  training_config: Record<string, unknown>
  metrics: Record<string, unknown>
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  parent_adapter_id?: string
  notes: string
  created_at: string
  deployed_at?: string
}

export interface BenchmarkResult {
  id: string
  adapter_id?: string
  base_model_id: string
  task: string
  score: number
  metrics: Record<string, unknown>
  samples: number
  config: Record<string, unknown>
  created_at: string
}

export interface ExperimentRecord {
  id: string
  experiment_type: string
  base_model_id: string
  adapter_id?: string
  config: Record<string, unknown>
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  metrics: Record<string, unknown>
  benchmark_ids: string[]
  started_at?: string
  completed_at?: string
  error?: string
  created_at: string
}

export interface GPUInfo {
  utilization: number
  memory_used: number
  memory_total: number
  memoryUsed: number
  memoryTotal: number
  temperature: number
  processes: number
}

export interface TrainingStatus {
  is_training: boolean
  current_job: string | null
  queue_length: number
  progress: number
  eta: string | null
  isTraining: boolean
  currentJob: string | null
  queueLength: number
}

export interface ConsentPrompt {
  recommendation_id: string
  title: string
  corrections_count: number
  estimated_improvement: number
  estimated_duration_min: number
  gpu_usage: string
  quality_score: number
  dataset_size: number
  message: string
}

export interface GovernorDecision {
  recommend: boolean
  reason: string
  details: Record<string, unknown>
  recommendation_id?: string
}

export interface TrainingRecommendation {
  id: string
  recommended_at: string
  status: string
  example_count: number
  avg_quality: number
  estimated_improvement: number
  estimated_duration_min: number
  contradiction_count: number
  duplicate_count: number
  diversity_score: number
  days_since_last_training: number
  decision_log: Record<string, unknown>
  approved_at?: string
  rejected_at?: string
}

export interface DashboardData {
  gpu: GPUInfo
  training: TrainingStatus
  models: ModelInfo[]
  adapters: AdapterRecord[]
  recent_benchmarks: BenchmarkResult[]
  recent_experiments: ExperimentRecord[]
}

export interface LogEntry {
  id: string
  level: "info" | "warn" | "error" | "debug" | "success"
  message: string
  source: string
  timestamp: string
}

export interface Notification {
  id: string
  type: "info" | "success" | "warning" | "error"
  title: string
  message: string
  timestamp: string
  read: boolean
  actionUrl?: string
}

// backward-compat aliases
export interface BaseModel {
  id: string
  name: string
  provider: string
  size: number
  quantization: string
  parameterCount: string
  isLoaded: boolean
}

export interface Adapter {
  id: string
  version: string
  baseModelId: string
  createdAt: string
  size: number
  metrics: AdapterMetrics | null
  status: "active" | "archived" | "failed"
}

export interface AdapterMetrics {
  accuracy: number
  latency: number
  evalScore: number
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  latency?: number
  model?: string
  rating?: "up" | "down" | null
}

export interface Benchmark {
  id: string
  name: string
  score: number
  previousScore?: number
  date: string
  modelVersion: string
}

export interface Experiment {
  id: string
  name: string
  status: "running" | "completed" | "failed" | "queued"
  progress: number
  startedAt: string
  completedAt?: string
  modelVersion: string
  datasetSize: number
  metrics: { loss: number; accuracy: number; evalScore: number }
}

export interface SahapathaStatus {
  buffer_size: number
  ready_to_train: boolean
  total_versions: number
  latest_version: number | null
  last_train_metrics: Record<string, unknown> | null
  last_train_time: number | null
  base_model: string
}

export interface SahapathaAdapter {
  version: string
  base_model: string
  adapter_path: string
  metrics: Record<string, unknown>
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: string
  updatedAt: string
  model: string
}

// --- Governor types (v2 Agent Platform) ---

export interface GovernorAgent {
  agent_id: string
  agent_type: string
  name: string
  description: string
  enabled: boolean
  status: string
  config: Record<string, unknown>
}

export interface AgentRun {
  run_id: string
  agent_id: string
  status: string
  started_at: string
  completed_at?: string
  result: Record<string, unknown>
  error?: string
  triggered_by: string
}

export interface GovernorDecision {
  knowledge_id?: string
  action: string
  confidence: number
  reasoning: string
  factors: Record<string, unknown>
  governed_at: string
}

export interface KGNode {
  id: string
  name: string
  node_type: string
  description: string
  tags: string[]
  aliases: string[]
}

export interface KGEdge {
  id: string
  source_id: string
  target_id: string
  edge_type: string
  weight: number
}

export interface KGConnection {
  edge_type: string
  weight: number
  connected_to: string
  connected_type: string
  direction: "outgoing" | "incoming"
}

export interface BenchmarkTask {
  id: string
  domain: string
  difficulty: string
  prompt: string
  expected_patterns: string[]
  description: string
  language: string
}

export interface BenchmarkSuite {
  domain: string
  total: number
  by_difficulty: Record<string, number>
}

export interface SchedulerJob {
  id: string
  name: string
  pipeline_name: string
  schedule_type: string
  interval_minutes: number
  enabled: boolean
  last_run?: string
  config: Record<string, unknown>
}

export interface EventBusStats {
  total_events: number
  events_by_type: Record<string, number>
  active_subscriptions: number
  queue_depth: number
  failed_events: number
}

export interface PipelineDefinition {
  name: string
  description: string
  steps: { agent_id: string; params: Record<string, unknown> }[]
  active: boolean
}

// --- Hermes Orchestrator types ---

export interface HermesAgent {
  id: string
  name: string
  type: string
  status: string
  enabled: boolean
}

export interface HermesStatus {
  status: string
  agents: HermesAgent[]
  pipelines: string[]
  event_bus: EventBusStats
  scheduler_running: boolean
}

export interface HermesRun {
  run_id: string
  agent_id: string
  status: string
  result: Record<string, unknown>
  error?: string
  started_at: string
  completed_at?: string
}

export interface HermesPipelineRun {
  pipeline: string
  steps: { step: number; agent: string; run_id: string; status: string; result_summary: string }[]
}

// --- Platform (consensus / feedback / routing / telemetry / alerts / profiler) ---

export interface CouncilVote {
  member: string
  relevance: number
  confidence: number
  risk: number
  preferred_action: string
  reasoning: string
}

export interface ConsensusDecision {
  knowledge_id: string
  action: string
  confidence: number
  consensus: number
  votes: CouncilVote[]
  disagreement: number
  majority_opposed: boolean
  decided_at: string
}

export interface TuningAdjustment {
  policy: string
  parameter: string
  before: number
  after: number
  direction: string
  reason: string
  task: string
}

export interface RouteResult {
  domain: string
  chosen_adapter: { adapter_id: string; benchmark_score: number; baseline_score: number; improvement: number }
  fallback: string
}

export interface TelemetryStats {
  total_runs: number
  total_gpu_hours: number
  total_cost_usd: number
  total_benchmark_delta: number
  cost_per_benchmark_point: number | null
  per_adapter: Record<string, { runs: number; gpu_hours: number; cost_usd: number; benchmark_delta: number; cost_per_point: number | null }>
}

export interface ProfileResult {
  dominant_stack: string
  stacks: { stack: string; weight: number; share: number; last_seen: string }[]
  sample_count: number
}
