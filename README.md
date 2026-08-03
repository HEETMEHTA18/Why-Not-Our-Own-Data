# Why Not Our Own Data? — Continuous Local LLM Personalization

**Tatvik + Sahapatha (सहपथ) + Governor**

A complete open-source stack for running, fine-tuning, and continuously improving a local language model on your own hardware. All data stays on your machine. Zero API keys required for inference.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Why Not Our Own Data?                         │
│  Continuous Local LLM Personalization — Research & Framework         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Tatvik        │    │   Sahapatha          │    │   Governor       │
│   AI Runtime    │    │   Self-Learning      │    │   Data Intel.    │
│   & Training    │◄──►│   LLM Framework      │◄──►│   & Governance   │
│   Platform      │    │   (सहपथ)             │    │   Engine         │
└────────┬────────┘    └──────────┬──────────┘    └────────┬─────────┘
         │                       │                         │
         │              ┌────────┴────────┐                │
         │              │ Continue.dev    │                │
         │              │ LSP / Autocomp. │                │
         │              │ (VS Code Ext.)  │                │
         │              └────────┬────────┘                │
         │                       │                         │
         ▼                       ▼                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         llama.cpp / llama-server                      │
│              (GPU-accelerated inference via Vulkan/CUDA)              │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Local LLM (GGUF format)                        │
│         Qwen2.5-Coder / DeepSeek-Coder / Bonsai-8B / Any GGUF        │
│         Loaded once, runs on NVIDIA RTX 4050 (6 GB VRAM)             │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Communication

```
┌───────────┐      HTTP/REST       ┌────────────┐      OpenAI API      ┌─────────┐
│  VS Code   │◄──────────────────►│  Tatvik API  │◄──────────────────►│  llama-  │
│  Continue  │    /models/chat     │  :8000      │   /v1/chat/         │  server  │
│  Dev LSP   │                     │             │   completions       │  :11434  │
└───────────┘                     └──────┬──────┘                     └─────────┘
                                         │
                                    ┌────┴────┐
                                    │ Sahapatha│
                                    │ (learn/  │
                                    │  train/  │
                                    │  status) │
                                    └─────────┘
```

---

## Components

### 1. Tatvik — AI Runtime & Training Platform (`tatvik/`)

FastAPI server orchestrating model inference, training, evaluation, deployment, and scheduling.

| Area | Endpoints | Purpose |
|------|-----------|---------|
| **Models** | `POST /models/chat`, `POST /models/generate` | Chat completions & text generation via llama-server |
| **Sahapatha** | `POST /sahapatha/learn`, `POST /sahapatha/train`, `GET /sahapatha/status` | Continuous learning loop |
| **Training** | `POST /training`, `GET /training/status` | QLoRA fine-tuning jobs |
| **Evaluation** | `POST /evaluation/run`, `GET /evaluation/benchmarks` | Model benchmark suites |
| **Registry** | `GET /registry/models`, `GET /registry/versions` | Model & adapter versioning |
| **Deployment** | `POST /deployment/deploy`, `POST /deployment/rollback` | Adapter deployment management |
| **System** | `GET /system/health`, `GET /system/gpu` | Health & GPU monitoring |

#### Key Files
- `tatvik/api/app.py` — FastAPI application entry point
- `tatvik/runtime/llama_client.py` — OpenAI-compatible client for llama-server
- `tatvik/runtime/models.py` — Pydantic request/response models
- `tatvik/runtime/manager.py` — Model lifecycle management
- `tatvik/api/deps.py` — Dependency injection container

### 2. Sahapatha — Self-Learning LLM Framework (`saha_patha/`)

Sanskrit: **सहपथ** (sa-ha-patha) — "together on the path". Continuous learning loop that captures user interactions, fine-tunes via QLoRA, and benchmarks improvements.

#### Core Loop
```
User Prompt → Data Collector → Buffer → Dataset Manager → Training Engine (QLoRA)
     ↓                                                          │
  Inference Engine ◄── Model Registry (v1, v2, ...) ◄──────────┘
     ↓
  Eval Harness → Benchmarks
     ↓
  Loop ──────────────────────────────────────────────────────────
```

#### Modules
| Module | File | Purpose |
|--------|------|---------|
| `Sahapatha` | `core/continuous_learner.py` | Main orchestrator for learn→train→eval cycle |
| `DataCollector` | `core/data_collector.py` | Captures prompt-response pairs to JSONL buffer |
| `DatasetManager` | `core/dataset_manager.py` | Dedup, format, split train/val |
| `TrainingEngine` | `core/training_engine.py` | QLoRA fine-tuning via transformers + peft |
| `ModelRegistry` | `core/model_registry.py` | Adapter versioning (v1, v2, ...) |
| `InferenceEngine` | `core/inference_engine.py` | Generation with base + adapter merge |
| `EvalHarness` | `core/eval_harness.py` | Async Python benchmark suite |
| `SahapathaConfig` | `core/config.py` | Configuration |

### 3. Governor — Data Intelligence Engine (`governor/`)

Data governance, classification, crawling, extraction, and quality assessment.

| Module | Purpose |
|--------|---------|
| `classifier/` | Intent/sentiment/text classification |
| `collector/` | Data ingestion from multiple sources |
| `crawler/` | Web + GitHub crawling |
| `dataset/` | Dataset construction & validation |
| `extractor/` | Structured extraction from raw data |
| `quality/` | Data quality assessment & scoring |
| `experiments/` | A/B experiment framework |
| `memory/` | Knowledge base & memory |
| `governor/` | Policy engine (core) |
| `consent/` | User consent & data rights |
| `research/` | Automated research engine |

### 4. Continue.dev LSP (VS Code Extension)

Open-source VS Code extension providing AI-powered chat and Tab autocomplete using the local model.

- **Config**: `~/.continue/config.json`
- **Provider**: OpenAI-compatible → `http://localhost:11434/v1`
- **Features**: Chat sidebar, inline Tab completion, codebase context, slash commands

### 5. Frontend — Next.js Dashboard (`src/`)

React/Next.js dashboard for monitoring, training, and interacting with the system.

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — GPU stats, training progress |
| `/analytics` | Benchmark charts & dataset growth |
| `/benchmarks` | Benchmark results |
| `/chat` | Chat interface |
| `/experiments` | Experiment list |
| `/models` | Model registry & adapter management |
| `/logs` | System log viewer |
| `/settings` | Configuration |

---

## Quick Start

### Prerequisites

- **Hardware**: NVIDIA GPU with 6+ GB VRAM (tested on RTX 4050)
- **Software**: CUDA 12.4, Python 3.12, Node.js 18+
- **Storage**: 10 GB free for model + adapters

### 1. Clone & Install

```bash
git clone <repo-url> && cd Why-Not-Our-Own-Data

# Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install torch==2.6.0+cu124 --index-url https://download.pytorch.org/whl/cu124
pip install transformers peft bitsandbytes datasets accelerate

# Node deps
npm install
```

### 2. Download a Model

```bash
# Install ollama (if not present)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a small working model
ollama pull qwen2.5-coder:0.5b

# Or use llama-server directly (for GGUF files)
# Download a GGUF from HuggingFace:
# https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF
```

### 3. Start Services

```bash
# Start llama-server (GGUF inference engine)
export LD_LIBRARY_PATH=/home/heet18/.hyperspace/bin
/path/to/llama-server \
  -m /path/to/model.gguf \
  --port 11434 -c 4096 --n-gpu-layers 99 --host 0.0.0.0

# Start Tatvik API server
cd tatvik
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Start frontend (optional)
npm run dev
```

### 4. Chat with the Model

```bash
# Via API
curl -X POST http://localhost:8000/models/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder-0.5b-q4_k_m.gguf","messages":[{"role":"user","content":"Write async Python"}],"stream":false}'

# Via Web UI
open http://localhost:8000/sahapatha/ui
```

### 5. Train (Continuous Learning)

```bash
# Learn from an interaction
curl -X POST http://localhost:8000/sahapatha/learn \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create async FastAPI endpoint","response":"@app.get(\"/items\") async def get_items(): return []"}'

# Check buffer
curl http://localhost:8000/sahapatha/status

# Start training (requires 5+ items in buffer)
curl -X POST http://localhost:8000/sahapatha/train
```

---

## Training Results

### QLoRA Fine-Tuning on DeepSeek-Coder-6.7B

**Dataset**: 32 async Python & FastAPI examples
**Hardware**: NVIDIA RTX 4050 (6 GB VRAM), CUDA 12.4
**Method**: 4-bit QLoRA (r=16, alpha=32)

```
╔══════════════════════════════════════════╗
║  Step    Epoch    Loss        Δ         ║
╠══════════════════════════════════════════╣
║     0     0.00    10.37     (baseline)  ║
║     5     0.62    10.37     -0.0%       ║
║    10     1.25    10.28     -0.9%       ║
║    15     1.88     9.83     -5.2%       ║
║    20     2.50     9.04    -12.8%       ║
║    25     3.12     8.58    -17.3%       ║
║    30     3.75     8.40    -19.0%       ║
║    35     4.38     8.24    -20.6%       ║
║    40     5.00     8.23    -20.7%       ║
╚══════════════════════════════════════════╝

  Loss reduction: 10.37 → 8.23 (20.7% improvement)
  Adapter size: 153 MB (LoRA weights only)
  Training time: ~5 minutes on RTX 4050
```

### Adapter Artifacts

```
saha_patha/adapters/deepseek-coder-6.7b-v1/
├── adapter_config.json          # LoRA config (r=16, alpha=32)
├── adapter_model.safetensors    # 153 MB trained weights
├── tokenizer_config.json
├── tokenizer.json
└── README.md

saha_patha/adapters/deepseek-coder-6.7b-v1/checkpoint-40/
├── trainer_state.json           # Per-step training metrics
├── optimizer.pt                 # AdamW state
├── scheduler.pt                 # LR scheduler
└── training_args.bin            # HF TrainingArguments
```

---

## LSP Integration (VS Code)

### What is LSP?

**Language Server Protocol** is the standard protocol editors use for code intelligence — autocomplete, go-to-definition, hover docs, diagnostics. By wrapping the local LLM behind an LSP server, your editor gets AI-powered inline code completions.

### Setup

1. **Install Continue.dev** in VS Code:
   ```bash
   code --install-extension continue.continue
   ```

2. **Configure** (`~/.continue/config.json`):
   ```json
   {
     "models": [{
       "title": "Qwen Coder Local",
       "provider": "openai",
       "model": "qwen2.5-coder-0.5b-q4_k_m.gguf",
       "apiBase": "http://localhost:11434/v1",
       "apiKey": "none"
     }],
     "tabAutocompleteModel": {
       "title": "Qwen Coder (Tab)",
       "provider": "openai",
       "model": "qwen2.5-coder-0.5b-q4_k_m.gguf",
       "apiBase": "http://localhost:11434/v1",
       "apiKey": "none"
     }
   }
   ```

3. **VS Code** → Click Continue icon in sidebar → Model should auto-connect to `localhost:11434`

### Features

- **Tab Autocomplete**: Inline code suggestions as you type
- **Chat**: Ask questions, refactor, explain code
- **Context**: @codebase, @problems, @search providers
- **Slash Commands**: /edit, /comment, /explain

---

## Research Context

This project is a research framework exploring:

1. **Continuous Local Personalization**: Can a model improve at code generation tasks through continued QLoRA fine-tuning on user interactions, without catastrophic forgetting?

2. **Adapter-Based Knowledge Accumulation**: Versioned LoRA adapters enable rollback, A/B comparison, and compositional fine-tuning. Each adapter captures a snapshot of learned behaviors.

3. **Data Sovereignty**: All training data and inference runs on local hardware. No data leaves the machine. This is increasingly relevant for regulated environments and privacy-conscious workflows.

4. **Self-Hosted Code Intelligence**: Replacing cloud-based code assistants (GitHub Copilot, etc.) with a locally fine-tuned model that learns project-specific patterns.

### Research Paper (In Progress)

The system is designed to support experiments that would feed into a research paper with sections on:

- Methodology: QLoRA for code domain adaptation
- Results: Loss curves, HumanEval scores, qualitative examples
- Ablation: Adapter merging strategies, dataset scaling, model sizes
- Related Work: LoRA, QLoRA, LLM fine-tuning, code generation
- Discussion: Limitations, privacy implications, future work

---

## Project Structure

```
Why-Not-Our-Own-Data/
├── tatvik/                  AI Runtime & Training Platform
│   ├── api/                 FastAPI routes (models, training, evaluation, etc.)
│   ├── runtime/             Client, models, manager
│   ├── training/            Training engine & adapter manager
│   ├── evaluation/          Benchmark engine & runner
│   ├── deployment/          Deployment & rollback managers
│   ├── registry/            Model & adapter registry
│   ├── scheduler/           Job queue & GPU scheduler
│   ├── monitor/             GPU monitoring
│   └── data/                Datasets & adapters
│
├── saha_patha/              Sahapatha Self-Learning Framework
│   ├── core/                Continuous learner, data collector, training, etc.
│   ├── scripts/             CLI pipeline
│   └── adapters/            Trained LoRA adapters
│
├── governor/                Data Intelligence Engine
│   ├── classifier/          Text classification
│   ├── collector/           Data ingestion
│   ├── crawler/             Web + GitHub crawling
│   ├── dataset/             Dataset building
│   ├── extractor/           Structured extraction
│   ├── quality/             Data quality scoring
│   ├── experiments/         A/B testing
│   ├── memory/              Knowledge base
│   ├── governor/            Policy engine
│   ├── consent/             Data rights
│   └── research/            Automated research
│
├── src/                     Next.js Frontend Dashboard
│   ├── app/                 Routes (dashboard, analytics, chat, etc.)
│   ├── components/          UI components (React + Radix)
│   └── hooks/               Data fetching hooks
│
├── run_lora.py              Standalone QLoRA training script
├── start_server.sh          Service startup script
├── package.json             Node dependencies
└── README.md                This file
```

---

## Environment

### Hardware (Tested)
| Component | Spec |
|-----------|------|
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU |
| VRAM | 6 GB GDDR6 |
| CUDA | 12.4 |
| CPU | 12th Gen Intel (20 threads) |
| RAM | 16 GB |
| OS | Pop!_OS 22.04 LTS (Linux) |

### Software Stack
| Tool | Version | Purpose |
|------|---------|---------|
| ollama | 0.32.3 | Model registry (optional) |
| llama-server | build 8148 | GGUF inference (Vulkan/CUDA) |
| CUDA | 12.4 | GPU acceleration |
| torch | 2.6.0+cu124 | Deep learning framework |
| transformers | 5.5.0 | Model loading & training |
| peft | 0.19.1 | LoRA/QLoRA adapters |
| bitsandbytes | 0.49.2 | 4-bit quantization |
| Python | 3.12 | Runtime language |

---

## License

MIT — Open source for community contribution and research.
