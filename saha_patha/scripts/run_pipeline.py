#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from saha_patha.core import Sahapatha
from saha_patha.core.config import SahapathaConfig


def main():
    parser = argparse.ArgumentParser(description="Sahapatha — Continuous Local LLM Personalization")
    parser.add_argument("--mode", choices=["train", "eval", "compare", "serve", "status", "interactive"], default="status")
    parser.add_argument("--model", default="deepseek-ai/deepseek-coder-6.7b-instruct")
    parser.add_argument("--dataset", help="Path to training dataset JSON")
    parser.add_argument("--prompt", help="Prompt for generation")
    parser.add_argument("--no-adapter", action="store_true", help="Use base model without adapter")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--benchmarks", help="Comma-separated coding benchmarks (humaneval,mbpp)")
    parser.add_argument("--max-samples", type=int, help="Max samples per benchmark (default from config)")
    parser.add_argument("--versions", help="Comma-separated adapter versions to compare against base")
    args = parser.parse_args()

    config = SahapathaConfig(base_model=args.model)
    if args.benchmarks:
        config.evaluation.benchmarks = [b.strip() for b in args.benchmarks.split(",")]
    if args.max_samples:
        config.evaluation.max_samples = args.max_samples
    sp = Sahapatha(config)

    if args.mode == "status":
        print(json.dumps(sp.status(), indent=2))

    elif args.mode == "train":
        if not args.dataset:
            print("Error: --dataset required for train mode", file=sys.stderr)
            sys.exit(1)
        result = sp.training.train(args.dataset)
        version = sp.registry.register(config.base_model, result["output_path"], result.get("metrics"))
        print(json.dumps({"version": version, **result}, indent=2))

    elif args.mode == "eval":
        if not args.prompt:
            latest = sp.registry.get_latest(sp.config.base_model)
            version = latest["version"] if latest else None
            print(json.dumps(sp.eval_harness.evaluate(sp.inference, version), indent=2))
        else:
            output = sp.answer(args.prompt, use_adapter=not args.no_adapter,
                               max_new_tokens=args.max_tokens, temperature=args.temperature)
            print(output)

    elif args.mode == "compare":
        versions = [v.strip() for v in (args.versions or "").split(",") if v.strip()]
        if not versions:
            versions = [v["version"] for v in sp.registry.list(sp.config.base_model)]
        print(f"Comparing base vs adapters {versions} on {config.evaluation.benchmarks}...")
        print(json.dumps(sp.eval_harness.compare(sp.inference, versions), indent=2))

    elif args.mode == "interactive":
        print("Sahapatha Interactive Mode. Type 'exit' to quit.")
        while True:
            try:
                prompt = input("\n>>> ")
            except (EOFError, KeyboardInterrupt):
                break
            if prompt.lower() in ("exit", "quit"):
                break
            if prompt.startswith("/train"):
                print("Running training cycle...")
                result = sp._run_training()
                print(json.dumps(result, indent=2)[:500])
                continue
            output = sp.answer(prompt, use_adapter=not args.no_adapter,
                               max_new_tokens=args.max_tokens, temperature=args.temperature)
            print(output)

    elif args.mode == "serve":
        print("API server mode — use Tatvik's existing API at port 8000")
        print("POST /v1/chat/completions with model='sahapatha' for adapter-injected inference")


if __name__ == "__main__":
    main()
