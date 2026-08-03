from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from .config import SahapathaConfig
from .model_registry import ModelRegistry


class InferenceEngine:
    def __init__(self, config: SahapathaConfig):
        self._config = config
        self._registry = ModelRegistry(config.adapter_dir)
        self._model: AutoModelForCausalLM | None = None
        self._tokenizer: AutoTokenizer | None = None
        self._base_loaded = False

    def load_base(self):
        if self._base_loaded:
            return
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        quant_config = BitsAndBytesConfig(
            load_in_4bit=self._config.load_in_4bit,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_quant_type=self._config.quant_type,
            bnb_4bit_use_double_quant=True,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self._config.base_model,
            quantization_config=quant_config,
            device_map="auto",
            torch_dtype=dtype,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(self._config.base_model)
        self._tokenizer.pad_token = self._tokenizer.eos_token
        self._base_loaded = True

    def load_adapter(self, version: str | None = None):
        self.load_base()
        latest = self._registry.get_latest(self._config.base_model) if version is None else \
                 self._registry.get(self._config.base_model, version)
        if not latest:
            raise ValueError(f"No adapter found for version={version}")
        adapter_path = latest["adapter_path"]
        self._model = PeftModel.from_pretrained(self._model, adapter_path)

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2, **kwargs) -> str:
        if self._tokenizer is None or self._model is None:
            self.load_base()
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            pad_token_id=self._tokenizer.eos_token_id,
            **kwargs,
        )
        return self._tokenizer.decode(outputs[0], skip_special_tokens=True)

    def generate_completion(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2, **kwargs) -> str:
        """Generate and return only the new tokens (strips the input prompt)."""
        if self._tokenizer is None or self._model is None:
            self.load_base()
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        input_len = inputs["input_ids"].shape[1]
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            pad_token_id=self._tokenizer.eos_token_id,
            **kwargs,
        )
        return self._tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
