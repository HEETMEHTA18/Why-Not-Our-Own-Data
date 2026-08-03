# Sahapatha (सहपथ) — Self-Learning LLM Framework

**Learn together, evolve continuously.**

Sahapatha is an open-source framework for **continuous local LLM personalization**. It enables any local language model to learn from user interactions, improve over time, and benchmark itself — all running on your own hardware with zero data leaving your machine.

## Architecture

```
User Prompt ──→ [Data Collector] ──→ Buffer (interactions.jsonl)
                                          │
                                    [Dataset Manager]
                                          │
                                   (dedup + format)
                                          │
                                    [Training Engine] ←── Base Model (4-bit QLoRA)
                                          │
                                    [Model Registry] (v1, v2, v3...)
                                          │
                                    [Inference Engine] (Base + Latest Adapter)
                                          │
                                    [Eval Harness] (benchmark suite)
                                          │
                                    User Feedback → loop
```

## Core Concepts

### 1. Adapter-Based Learning
Only tiny adapter matrices (~40 MB) are trained — not the full 6.7B model. The base model stays frozen. Swappable, versioned, no regression risk.

### 2. Continuous Cycle
- **Record**: Every prompt-response pair is captured
- **Curation**: Duplicates and low-quality data are filtered
- **Train**: QLoRA fine-tuning runs async (doesn't block inference)
- **Register**: Each adapter version is saved with benchmark scores
- **Evaluate**: Run against async Python/FastAPI benchmarks
- **Loop**: The cycle repeats as data accumulates

### 3. Local-First
- All data stays on your machine
- No API keys needed (uses local inference with Ollama or HuggingFace)
- Fully offline capable after model is cached

## Quick Start

```bash
# Install
pip install torch transformers peft bitsandbytes datasets accelerate

# Train from dataset
python scripts/run_pipeline.py --mode train --dataset your_data.json

# Interactive mode
python scripts/run_pipeline.py --mode interactive

# Evaluate
python scripts/run_pipeline.py --mode eval

# Check status
python scripts/run_pipeline.py --mode status
```

## Training Dataset Format

```json
[
  {
    "instruction": "Create a FastAPI endpoint with async database session",
    "input": "",
    "output": "from __future__ import annotations\nfrom sqlalchemy.ext.asyncio import AsyncSession..."
  }
]
```

## Benchmarks

Built-in async Python & FastAPI benchmarks evaluate adapter quality:

| Benchmark | Description |
|-----------|-------------|
| `async_python` | Async/await, httpx, aiofiles, asyncio patterns |
| `fastapi` | Route handlers, dependencies, middleware, lifespan |

Planned: HumanEval, MBPP streaming integration.

## Integration with Tatvik

Sahapatha integrates with Tatvik's existing infrastructure:
- Uses Tatvik's API server for inference
- Adapters stored in Tatvik's registry format
- Training leverages Tatvik's training engine

## Project Structure

```
saha_patha/
├── core/
│   ├── continuous_learner.py   # Main orchestrator
│   ├── data_collector.py       # Interaction capture
│   ├── dataset_manager.py      # Curation & management
│   ├── training_engine.py      # QLoRA fine-tuning
│   ├── model_registry.py       # Versioned adapters
│   ├── inference_engine.py     # Adapter-aware inference
│   ├── eval_harness.py         # Benchmark evaluation
│   └── config.py               # Configuration
├── scripts/
│   └── run_pipeline.py         # CLI entrypoint
├── adapters/                   # Trained adapters
├── datasets/                   # Training data
└── tests/                      # Test suite
```

## License

MIT — Open source for community contribution.
