from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable
from uuid import uuid4

import structlog
from tenacity import retry, stop_after_attempt, wait_fixed

from registry.manager import RegistryManager
from registry.models import AdapterRecord
from shared.config import settings
from shared.types import Status

from .adapter import AdapterManager
from .config import TrainingConfig

logger = structlog.get_logger()


class TrainingEngine:
    def __init__(self, registry: RegistryManager, adapter_manager: AdapterManager | None = None) -> None:
        self._registry = registry
        self._adapter_manager = adapter_manager or AdapterManager()
        self._cancel_requested: bool = False
        self._on_progress: Callable[[dict[str, Any]], None] | None = None

    def set_progress_callback(self, callback: Callable[[dict[str, Any]], None] | None) -> None:
        self._on_progress = callback

    async def train(
        self,
        config: TrainingConfig,
        experiment_id: str | None = None,
    ) -> AdapterRecord:
        self._cancel_requested = False

        base_model_id = config.model_name.replace(":", "-").replace("/", "-")
        adapter = await self._registry.create_adapter(
            base_model_id=base_model_id,
            dataset_id=Path(config.dataset_path).stem,
            training_config=config.model_dump(),
            notes=f"Training {config.model_name} on {config.dataset_path}",
        )
        logger.info("training_adapter_created", adapter_id=adapter.id, version=adapter.version)

        await self._registry.update_adapter_status(adapter.id, Status.RUNNING)

        try:
            self._emit_progress({"adapter_id": adapter.id, "status": "preparing", "progress": 0.0})

            result = await self._run_training_script(config, adapter)

            await self._registry.update_adapter_status(
                adapter.id, Status.COMPLETED,
                metrics=result.get("metrics", {}),
            )
            adapter_dir = self._adapter_manager.save_adapter_metadata(
                adapter_id=adapter.id,
                base_model=config.model_name,
                version=adapter.version,
                config=config.model_dump(),
                metrics=result.get("metrics", {}),
            )
            await self._registry.update_adapter_path(adapter.id, str(adapter_dir))
            await self._registry.update_adapter_status(adapter.id, Status.COMPLETED)

            self._emit_progress({
                "adapter_id": adapter.id, "status": "completed",
                "progress": 1.0, "metrics": result.get("metrics", {}),
                "path": str(adapter_dir),
            })
            logger.info("training_completed", adapter_id=adapter.id, path=str(adapter_dir))

        except Exception as e:
            logger.error("training_failed", adapter_id=adapter.id, error=str(e))
            await self._registry.update_adapter_status(adapter.id, Status.FAILED, metrics={"error": str(e)})
            self._emit_progress({"adapter_id": adapter.id, "status": "failed", "error": str(e)})
            raise

        return adapter

    async def _run_training_script(self, config: TrainingConfig, adapter: AdapterRecord) -> dict[str, Any]:
        script_path = self._get_training_script()
        output_json = settings.data_dir / "experiments" / f"train_{adapter.id}.json"

        env = os.environ.copy()
        env.update({
            "TATVIK_MODEL": config.model_name,
            "TATVIK_DATASET": config.dataset_path,
            "TATVIK_OUTPUT_DIR": config.output_dir,
            "TATVIK_ADAPTER_ID": adapter.id,
            "TATVIK_ADAPTER_VERSION": str(adapter.version),
            "TATVIK_NUM_EPOCHS": str(config.num_epochs),
            "TATVIK_LEARNING_RATE": str(config.learning_rate),
            "TATVIK_BATCH_SIZE": str(config.batch_size),
            "TATVIK_MAX_SEQ_LENGTH": str(config.max_seq_length),
            "TATVIK_LORA_R": str(config.lora.r),
            "TATVIK_LORA_ALPHA": str(config.lora.lora_alpha),
            "TATVIK_LORA_DROPOUT": str(config.lora.lora_dropout),
            "TATVIK_USE_UNSLOTH": str(config.use_unsloth).lower(),
            "TATVIK_QUANT_METHOD": config.quantization.method.value,
            "TATVIK_OUTPUT_JSON": str(output_json),
            "TATVIK_RESUME": config.resume_from_checkpoint or "",
            "TATVIK_GRADIENT_CHECKPOINTING": str(config.use_gradient_checkpointing).lower(),
            "TATVIK_WANDB_DISABLED": "true",
        })

        logger.info("launching_training_script", script=str(script_path))

        def run():
            result = subprocess.run(
                [sys.executable, str(script_path)],
                env=env,
                cwd=settings.data_dir.parent,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Training script failed:\n{result.stderr}")
            return result

        loop = __import__("asyncio").get_event_loop()
        result = await loop.run_in_executor(None, run)

        if output_json.exists():
            return json.loads(output_json.read_text())
        return {"metrics": {}, "output_path": config.output_dir}

    def _get_training_script(self) -> Path:
        script = settings.data_dir.parent / "training" / "run_training.py"
        if not script.exists():
            script = self._generate_training_script(script)
        return script

    def _generate_training_script(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = r'''#!/usr/bin/env python3
"""Tatvik Training Script — generated by TrainingEngine."""
import json
import os
import sys

def main():
    model = os.environ["TATVIK_MODEL"]
    dataset = os.environ["TATVIK_DATASET"]
    output_dir = os.environ["TATVIK_OUTPUT_DIR"]
    adapter_id = os.environ["TATVIK_ADAPTER_ID"]
    version = int(os.environ["TATVIK_ADAPTER_VERSION"])
    num_epochs = int(os.environ["TATVIK_NUM_EPOCHS"])
    lr = float(os.environ["TATVIK_LEARNING_RATE"])
    batch_size = int(os.environ["TATVIK_BATCH_SIZE"])
    max_seq_length = int(os.environ["TATVIK_MAX_SEQ_LENGTH"])
    lora_r = int(os.environ["TATVIK_LORA_R"])
    lora_alpha = int(os.environ["TATVIK_LORA_ALPHA"])
    lora_dropout = float(os.environ["TATVIK_LORA_DROPOUT"])
    use_unsloth = os.environ["TATVIK_USE_UNSLOTH"] == "true"
    quant_method = os.environ["TATVIK_QUANT_METHOD"]
    output_json = os.environ["TATVIK_OUTPUT_JSON"]
    resume = os.environ.get("TATVIK_RESUME", "")
    grad_ckpt = os.environ.get("TATVIK_GRADIENT_CHECKPOINTING", "true") == "true"

    # -- Import training libraries --
    try:
        if use_unsloth:
            from unsloth import FastLanguageModel, is_bfloat16_supported
            from unsloth.chat_templates import get_chat_template
            from unsloth import UnslothTrainer, UnslothTrainingArguments
            from unsloth import UnslothDataCollator
        else:
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
            from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
            from datasets import load_dataset
    except ImportError as e:
        result = {"metrics": {"error": f"Import failed: {e}"}, "note": "training libs not installed"}
        with open(output_json, "w") as f:
            json.dump(result, f)
        if not use_unsloth:
            print(f"Training libraries not available: {e}", file=sys.stderr)
            return result

    # -- Load dataset --
    from datasets import load_dataset
    print(f"Loading dataset: {dataset}")
    dataset_data = load_dataset("json", data_files=dataset, split="train")

    # -- Load model and tokenizer --
    print(f"Loading model: {model}")
    model_kwargs = dict(
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=(quant_method in ("nf4", "fp4", "int4")),
    )

    if use_unsloth:
        model_for_training, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model,
            **model_kwargs,
        )
        model_for_training = FastLanguageModel.get_peft_model(
            model_for_training,
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            use_gradient_checkpointing=grad_ckpt,
            random_state=42,
        )
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        import torch
        quantization_config = None
        if quant_method in ("nf4", "fp4", "int4"):
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4" if quant_method == "nf4" else "fp4",
            )

        model_for_training = AutoModelForCausalLM.from_pretrained(
            model, quantization_config=quantization_config,
            device_map="auto", torch_dtype=torch.bfloat16,
        )
        tokenizer = AutoTokenizer.from_pretrained(model)
        tokenizer.pad_token = tokenizer.eos_token

        model_for_training = prepare_model_for_kbit_training(model_for_training)
        lora_config = LoraConfig(
            r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            task_type="CAUSAL_LM",
        )
        model_for_training = get_peft_model(model_for_training, lora_config)

    # -- Tokenize dataset --
    def tokenize_fn(examples):
        return tokenizer(examples["text"] if "text" in examples else examples["instruction"],
                         truncation=True, padding=False, max_length=max_seq_length)

    if "text" in dataset_data.column_names:
        tokenized = dataset_data.map(tokenize_fn, batched=True, remove_columns=dataset_data.column_names)
    elif "instruction" in dataset_data.column_names:
        def fmt(example):
            prompt = example.get("instruction", "")
            inp = example.get("input", "")
            out = example.get("output", "")
            full = f"### Instruction:\n{prompt}\n"
            if inp:
                full += f"### Input:\n{inp}\n"
            full += f"### Response:\n{out}"
            return {"text": full}
        formatted = dataset_data.map(fmt)
        tokenized = formatted.map(tokenize_fn, batched=True, remove_columns=formatted.column_names)
    else:
        tokenized = dataset_data.map(tokenize_fn, batched=True)

    # -- Training arguments --
    training_args_kwargs = dict(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=lr,
        warmup_steps=100,
        logging_steps=10,
        save_steps=0,
        save_total_limit=2,
        optim="adamw_8bit",
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=not __import__("torch").cuda.is_bf16_supported() if hasattr(__import__("torch").cuda, "is_bf16_supported") else False,
        bf16=hasattr(__import__("torch").cuda, "is_bf16_supported") and __import__("torch").cuda.is_bf16_supported(),
        report_to="none",
        ddp_find_unused_parameters=False,
        gradient_checkpointing=grad_ckpt,
        resume_from_checkpoint=resume or None,
    )

    if use_unsloth:
        trainer = UnslothTrainer(
            model=model_for_training,
            tokenizer=tokenizer,
            train_dataset=tokenized,
            args=UnslothTrainingArguments(**training_args_kwargs),
            data_collator=UnslothDataCollator(tokenizer, max_seq_length=max_seq_length),
        )
    else:
        from transformers import Trainer, TrainingArguments
        trainer = Trainer(
            model=model_for_training,
            tokenizer=tokenizer,
            train_dataset=tokenized,
            args=TrainingArguments(**training_args_kwargs),
        )

    # -- Train --
    print("Starting training...")
    trainer.train(resume_from_checkpoint=resume or None)

    # -- Save adapter --
    adapter_save_path = os.path.join(output_dir, f"v{version}")
    os.makedirs(adapter_save_path, exist_ok=True)
    if use_unsloth:
        model_for_training.save_pretrained(adapter_save_path)
        tokenizer.save_pretrained(adapter_save_path)
    else:
        model_for_training.save_pretrained(adapter_save_path)
        tokenizer.save_pretrained(adapter_save_path)

    print(f"Adapter saved to: {adapter_save_path}")

    # -- Collect metrics --
    metrics = {}
    if hasattr(trainer, "state") and trainer.state.log_history:
        last_log = [l for l in trainer.state.log_history if "loss" in l]
        if last_log:
            metrics["final_loss"] = last_log[-1].get("loss", 0.0)
            metrics["best_loss"] = min(l.get("loss", float("inf")) for l in last_log)
            metrics["epochs_completed"] = len(last_log)

    result = {"metrics": metrics, "output_path": adapter_save_path}
    with open(output_json, "w") as f:
        json.dump(result, f)
    print(f"Results written to: {output_json}")
    return result

if __name__ == "__main__":
    main()
'''
        path.write_text(content)
        os.chmod(path, 0o755)
        logger.info("training_script_generated", path=str(path))
        return path

    def request_cancel(self) -> None:
        self._cancel_requested = True
        logger.info("training_cancel_requested")

    def _emit_progress(self, data: dict[str, Any]) -> None:
        if self._on_progress:
            self._on_progress(data)
