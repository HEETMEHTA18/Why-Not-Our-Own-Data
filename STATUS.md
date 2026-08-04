# Tatvik Platform — Current Status & Roadmap

**Stage: working local platform (v0.1)** · Last updated: 2026-08-03

This document is the single source of truth for *where the project stands right now*:
what works, what is real vs simulated, how to run/verify everything, and what to build next.

---

## 1. How to run / verify

### Services (systemd user units — all five)

| Port | Service | Unit | Health path |
|------|---------|------|-------------|
| 11434 | llama-server (GGUF inference) | `tatvik-llama.service` | `/health` |
| 8000 | Tatvik API (FastAPI) | `tatvik-api.service` | `/system/health` |
| 8100 | Governor (data intel, agents, KG) | `governor.service` | `/health` |
| 8101 | Hermes (multi-agent orchestrator) | `hermes.service` | `/health` |
| 3000 | Next.js frontend | `tatvik-front.service` | `/chat` |

```bash
# One-stop control (status/start/stop/restart/logs/build/verify)
./scripts/tatvik.sh status
./scripts/tatvik.sh restart
./scripts/tatvik.sh logs
./scripts/tatvik.sh build     # rebuild frontend + restart
./scripts/tatvik.sh verify    # full end-to-end feature check
```

### End-to-end verification

```bash
./scripts/verify.sh
```

Covers: service liveness, chat + system prompt identity, SSE streaming, RAG context
search, web search, Sahapatha trained-model chat, Kronos forecast, Hermes agent
registration/execution, GPU monitor.

### Backend dev server (non-systemd alternative)

`start_server.sh` is the legacy nohup launcher. Prefer systemd units via `scripts/tatvik.sh`.

---

## 2. What is REAL (production data, wired to real endpoints)

| Area | How it works | Status |
|------|--------------|--------|
| **Model inference** | llama-server on :11434; API proxies `/models/chat`, `/models/generate`, SSE stream | ✅ real |
| **Benchmark evaluation** | `LlamaCppCompletionsAPI` in `tatvik/evaluation/llama_cpp_lm.py` loads the GGUF in-process (`logits_all=True`) and runs real lm_eval tasks (loglikelihood + generation). Results written to the registry DB with real scores/samples. | ✅ real |
| **Registry** | base models + adapter versions + benchmark results persisted in SQLite under `tatvik/data/registry/` | ✅ real |
| **Training jobs** | QLoRA jobs through the scheduler job queue; status/adapters endpoints | ✅ real |
| **Deployment/rollback** | deploy/rollback/should-rollback/compare endpoints wired to frontend adapter list | ✅ real |
| **Settings** | `GET/PUT /system/settings` reads/writes `shared/config.py` + persists to `.env` (`TATVIK_TRAINING_DEFAULT_*`); Settings page fully functional | ✅ real |
| **Logs** | `GET /system/logs` aggregates scheduler jobs + benchmark records + sahapatha status; Logs page uses it | ✅ real |
| **Governor** | recommendations, council consensus, feedback/tuning thresholds, agents, pipelines, knowledge graph — all real endpoints, all used | ✅ real |
| **Hermes** | 8 agents, pipelines, run history, event bus — real endpoints, auto-polled | ✅ real |
| **Analytics charts** | benchmark-chart = real `/evaluation/benchmarks`; dataset-growth = real governor collector+dataset stats | ✅ real |
| **Forecast (Kronos)** | `POST /forecast/predict` runs the fine-tuned Kronos model against live yfinance data | ✅ real |

### Dashboard & model info
- Dashboard KPIs, GPU monitor, training progress, service health, recent activity → real API data.
- GPU "processes" row **removed** (no backend source — the monitor doesn't report it).
- Context-window card shows the configured window + compression status from `/system/health` (no fabricated token-usage estimate).

---

## 3. What is SIMULATED or intentionally static (known, not hidden)

These are intentional and documented — not silently-fake data:

| Item | Where | Why |
|------|-------|-----|
| Benchmark suite task list | `src/app/benchmarks/page.tsx` `SUITE_TASKS` | UI constant for "Run All"; task set is also defined backend-side in `evaluation/models.py` `STANDARD_SUITES` |
| Forecast ticker dropdown | `src/app/forecast/page.tsx` | Static NSE symbol list — the backend `/forecast/tickers` returns the identical list |
| Sample knowledge ingestion | `src/app/intelligence/page.tsx` | Button *deliberately* ingests a fixed sample doc into the real KG backend |
| `previousScore` = undefined | `src/app/page.tsx` | No historical benchmark tracking yet; regression deltas won't show until we store per-version baselines |

---

## 4. Known gaps / things to fix next

### Backend
- **Hermes restart note**: `HermesSettings` must keep `extra="ignore"` — the `.env` `TATVIK_*` vars used to crash it (fixed in `hermes/config.py`).
- **Benchmark per-version baselines**: to show regression deltas in the dashboard, persist a `previous_score` per benchmark task/version.
- **GPU process count**: no real source; the row was removed from the UI. Add nvidia-smi process parsing if needed.
- **Kronos forecast model**: ensure `kronos/` model weights are present for `POST /forecast/predict` (falls back to a small bundled model otherwise).

### Frontend (already mostly wired — remaining polish)
- Agents page "Pipelines" tab now loads `/agents/pipeline/list`; "Run History" loads `/agents/runs`.
- Approval "Tuning history" loads `/platform/feedback/history`.
- No page-level loading/error skeletons on some tabs (cosmetic).

### Data-hygiene
- `.env` contains a live SuperCompress API key — it is **gitignored**; only `.env.example` is committed. Do not commit the real key.

---

## 5. Architecture map

```
Browser (Next.js :3000)
   │  fetch
   ▼
Tatvik API (:8000) ──proxies──► llama-server (:11434)  [inference]
   │   ├─ /models, /training, /evaluation, /deployment, /registry, /system
   │   ├─ /sahapatha  (continuous learning: learn → train → status)
   │   └─ /forecast   (Kronos time-series)
   │
   ├─ Governor (:8100)  — recommendations, council, feedback/tuning, agents,
   │                     pipelines, knowledge graph, dataset/collector
   │
   └─ Hermes (:8101)    — multi-agent orchestrator (8 agents), pipelines, event bus
```

### Key source files
| Concern | Path |
|---------|------|
| Real eval adapter | `tatvik/evaluation/llama_cpp_lm.py` |
| Eval runner | `tatvik/evaluation/runner.py` |
| Settings/logs endpoints | `tatvik/api/routes/system.py` |
| Settings model | `tatvik/shared/config.py` |
| Frontend API client | `src/lib/api.ts` |
| Service control | `scripts/tatvik.sh` + `~/.config/systemd/user/*.service` |

---

## 6. Roadmap

### Done (checkpointed in git)
- [x] Real lm_eval benchmark execution (loglikelihood + generation) through the Tatvik runner
- [x] Settings page + backend persistence
- [x] Real system logs endpoint + page
- [x] Benchmark "Run All"/"Run" and models Pull/Delete wired
- [x] Analytics charts off real data
- [x] Adapter Archive→Deploy/Rollback wired
- [x] Agents pipelines + run history wired
- [x] Approval tuning history wired
- [x] Hermes crash fix, Governor as a managed systemd service
- [x] Git checkpoint + `.gitignore` + `.env.example`

### Next
- [ ] Per-version benchmark baselines (regression deltas in UI)
- [ ] GPU process count via nvidia-smi parsing
- [ ] Page-level loading/error states + auto-refresh where stale
- [ ] End-to-end test covering one full train→eval→deploy cycle
- [ ] Package/export of a trained adapter and a documented rollback drill

---

## 7. Ports & auth notes

- No auth on any service (localhost-only research deployment).
- Hermes agents are enabled in `hermes/` config; Governor runs its scheduler/event bus by default.
- SuperCompress: `.env` controls enablement/key; falls back to a free local policy when no key is set.
