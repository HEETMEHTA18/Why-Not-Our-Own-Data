from __future__ import annotations

import json
import gc
import torch
from pathlib import Path
from typing import Any

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

from .config import SahapathaConfig


class TrainingEngine:
    def __init__(self, config: SahapathaConfig):
        self._config = config

    def train(
        self,
        dataset_path: str,
        adapter_name: str | None = None,
    ) -> dict[str, Any]:
        cfg = self._config.training
        adapter_name = adapter_name or f"adapter-{__import__('uuid').uuid4().hex[:8]}"
        output_dir = Path(self._config.adapter_dir) / self._config.base_model.replace("/", "-") / adapter_name
        output_dir.mkdir(parents=True, exist_ok=True)

        torch.cuda.empty_cache()
        gc.collect()

        bf16 = torch.cuda.is_bf16_supported()
        dtype = torch.bfloat16 if bf16 else torch.float16

        quant_config = BitsAndBytesConfig(
            load_in_4bit=self._config.load_in_4bit,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_quant_type=self._config.quant_type,
            bnb_4bit_use_double_quant=True,
        )

        print(f"Loading model: {self._config.base_model}")
        model = AutoModelForCausalLM.from_pretrained(
            self._config.base_model,
            quantization_config=quant_config,
            device_map="auto",
            torch_dtype=dtype,
        )
        tokenizer = AutoTokenizer.from_pretrained(self._config.base_model)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

        modules = cfg.lora.target_modules or ["q_proj", "k_proj", "v_proj", "o_proj",
                                               "gate_proj", "up_proj", "down_proj"]
        lora_cfg = LoraConfig(
            r=cfg.lora.r,
            lora_alpha=cfg.lora.alpha,
            lora_dropout=cfg.lora.dropout,
            target_modules=modules,
            task_type="CAUSAL_LM",
            bias="none",
        )
        model = get_peft_model(model, lora_cfg)
        trainable = model.print_trainable_parameters()

        from datasets import load_dataset as load_ds
        dataset = load_ds("json", data_files=dataset_path, split="train")

        def fmt(ex):
            instruction = ex.get("instruction", "")
            inp = ex.get("input", "")
            output = ex.get("output", "")
            text = f"### Instruction:\n{instruction}\n"
            if inp:
                text += f"### Input:\n{inp}\n"
            text += f"### Response:\n{output}"
            return {"text": text}

        dataset = dataset.map(fmt, remove_columns=dataset.column_names)

        def tok(ex):
            res = tokenizer(ex["text"], truncation=True, padding=False, max_length=cfg.max_seq_length)
            res["labels"] = res["input_ids"].copy()
            return res

        dataset = dataset.map(tok, batched=True, remove_columns=["text"])

        args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=cfg.num_epochs,
            per_device_train_batch_size=cfg.batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            learning_rate=cfg.learning_rate,
            warmup_steps=cfg.warmup_steps,
            logging_steps=cfg.logging_steps,
            save_steps=cfg.save_steps,
            save_total_limit=2,
            optim=cfg.optim,
            lr_scheduler_type=cfg.lr_scheduler,
            weight_decay=cfg.weight_decay,
            max_grad_norm=1.0,
            fp16=not bf16,
            bf16=bf16,
            report_to="none",
            ddp_find_unused_parameters=False,
            gradient_checkpointing=True,
            remove_unused_columns=False,
            dataloader_num_workers=0,
        )

        collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True, max_length=cfg.max_seq_length)
        trainer = Trainer(model=model, train_dataset=dataset, args=args, data_collator=collator)

        print("Starting training...")
        trainer.train()

        model.save_pretrained(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))

        losses = [l.get("loss") for l in trainer.state.log_history if "loss" in l]
        metrics = {
            "final_loss": losses[-1] if losses else None,
            "best_loss": min(losses) if losses else None,
            "epochs": cfg.num_epochs,
            "trainable_params": trainable if isinstance(trainable, str) else "",
        }

        result = {"metrics": metrics, "output_path": str(output_dir), "adapter_name": adapter_name}
        with open(output_dir / "training_result.json", "w") as f:
            json.dump(result, f, indent=2)

        torch.cuda.empty_cache()
        gc.collect()

        return result
