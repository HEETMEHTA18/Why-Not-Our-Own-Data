"""
Run focused code training with increased epochs using the curated dataset.
"""

import json
import sys
import os
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from saha_patha.core.config import SahapathaConfig, TrainingParams, LoraParams
from saha_patha.core.training_engine import TrainingEngine

model_path = os.path.expanduser("~/.cache/huggingface/hub/Qwen2.5-Coder-0.5B-Instruct")

config = SahapathaConfig(
    base_model=model_path,
    adapter_dir=str(Path(project_root) / "saha_patha" / "adapters"),
    dataset_dir=str(Path(project_root) / "saha_patha" / "datasets"),
    training=TrainingParams(
        num_epochs=20,
        learning_rate=1e-4,
        batch_size=1,
        gradient_accumulation_steps=4,
        max_seq_length=2048,
        warmup_steps=10,
        logging_steps=5,
        lora=LoraParams(r=16, alpha=32, dropout=0.05),
    ),
)

dataset_path = str(Path(project_root) / "saha_patha" / "datasets" / "code_training_v1.json")
print(f"Loading dataset from: {dataset_path}")
with open(dataset_path) as f:
    data = json.load(f)
print(f"Dataset has {len(data)} examples")
print(f"First: {data[0]['instruction'][:60]}...")
print(f"Last:  {data[-1]['instruction'][:60]}...")
print()

# Run training directly
engine = TrainingEngine(config)
result = engine.train(dataset_path, adapter_name="code-v1")

print(f"\nTraining complete!")
print(f"  Adapter: {result['adapter_name']}")
print(f"  Output: {result['output_path']}")
print(f"  Metrics: {json.dumps(result.get('metrics', {}), indent=2)}")
