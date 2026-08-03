"""
CLI for Tatvik — chat with the local model from terminal.
Automatically captures interactions for continuous learning.
"""

import json
import sys

import httpx

API = "http://localhost:8000"


def _get_model() -> str:
    try:
        r = httpx.get(f"{API}/models", timeout=5)
        models = r.json()
        if models:
            return models[0].get("name") or models[0].get("model", "")
    except Exception:
        pass
    return "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"


def chat(prompt: str, model: str = "") -> str:
    model = model or _get_model()
    r = httpx.post(
        f"{API}/models/chat",
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", "")


def learn(prompt: str, response: str) -> None:
    httpx.post(
        f"{API}/sahapatha/learn",
        json={"prompt": prompt, "response": response},
        timeout=10,
    )


def status() -> dict:
    r = httpx.get(f"{API}/sahapatha/status", timeout=10)
    return r.json()


def interactive() -> None:
    model = _get_model()
    print(f"Tatvik CLI — model: {model}")
    print("Type messages. Blank line runs train. Ctrl+D to exit.")
    print()

    while True:
        try:
            lines = []
            while True:
                line = input(">>> " if not lines else "... ")
                if not line and not lines:
                    print("(empty = show status)")
                    s = status()
                    print(f"  buffer: {s['buffer_size']}, adapters: {s['total_versions']}, last: {s['latest_version'] or '—'}")
                    continue
                if not line:
                    break
                lines.append(line)
            prompt = "\n".join(lines)

            if prompt == "train":
                r = httpx.post(f"{API}/sahapatha/train", timeout=600)
                print(f"Train result: {r.json()}")
                continue

            if prompt == "status":
                s = status()
                print(json.dumps(s, indent=2))
                continue

            response = chat(prompt, model)
            print(f"\n{response}\n")

            learn(prompt, response)
            s = status()
            print(f"[saved — buffer: {s['buffer_size']}]")
        except (EOFError, KeyboardInterrupt):
            print()
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        resp = chat(prompt)
        print(resp)
        learn(prompt, resp)
    else:
        interactive()