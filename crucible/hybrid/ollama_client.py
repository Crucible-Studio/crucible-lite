"""
Ollama wrapper — local LLM access for Crucible agents.

Corpus contract:
  input tier:  PUBLIC or DERIVED-OK only
  execution:   local
  model:       configurable via CRUCIBLE_LOCAL_MODEL env var
               default qwen2.5:0.5b (zero-shot, no fine-tuning required)
               override to any Ollama-hosted model

Inference path for Qwen family (qwen2.5:*):
  Must use /api/generate with raw=True and explicit Qwen chat template tokens.
  /api/chat auto-template detection does not correctly apply the chat template
  for GGUF-backed models, causing base-model freeform output instead of JSON.

Usage (library):
  from crucible.hybrid.ollama_client import LocalLLM
  llm = LocalLLM()
  response = llm.chat("parse this table and return JSON: ...")

Usage (CLI smoke test):
  python -m crucible.hybrid.ollama_client
"""

import json
import os
from typing import Generator, Optional

import requests

DEFAULT_HOST  = os.environ.get("OLLAMA_HOST",          "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("CRUCIBLE_LOCAL_MODEL", "qwen2.5:0.5b")

TIMEOUT = (5, 600)

_RAW_QWEN_MODELS = {"qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b"}


def _qwen_prompt(system: Optional[str], user: str) -> str:
    parts = []
    if system:
        parts.append(f"<|im_start|>system\n{system}<|im_end|>")
    parts.append(f"<|im_start|>user\n{user}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


class LocalLLM:
    """
    Thin wrapper around Ollama /api/generate and /api/chat.

    Corpus contract:
      - Never pass PRIVATE content into prompts — caller is responsible
      - Input tier: PUBLIC or DERIVED-OK only
      - Output tier: DERIVED-OK (model outputs are treated as derived summaries)
    """

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
        self.model    = model
        self.host     = host
        self.chat_url = f"{host}/api/chat"
        self.gen_url  = f"{host}/api/generate"
        self._use_raw = any(m in model for m in _RAW_QWEN_MODELS)

    def _post_raw(self, system: Optional[str], user: str, stream: bool) -> requests.Response:
        payload = {
            "model":   self.model,
            "prompt":  _qwen_prompt(system, user),
            "raw":     True,
            "stream":  stream,
            "options": {"temperature": 0.0, "stop": ["<|im_end|>"]},
        }
        return requests.post(self.gen_url, json=payload, stream=stream, timeout=TIMEOUT)

    def _post_chat(self, system: Optional[str], user: str, stream: bool) -> requests.Response:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        payload = {"model": self.model, "messages": messages, "stream": stream}
        return requests.post(self.chat_url, json=payload, stream=stream, timeout=TIMEOUT)

    def chat(self, prompt: str, system: Optional[str] = None) -> str:
        """Single-turn blocking chat. Returns full response string."""
        if self._use_raw:
            resp = self._post_raw(system, prompt, stream=True)
            resp.raise_for_status()
            chunks = []
            for raw in resp.iter_lines():
                if not raw:
                    continue
                chunk = json.loads(raw)
                chunks.append(chunk.get("response", ""))
                if chunk.get("done"):
                    break
            return "".join(chunks)

        resp = self._post_chat(system, prompt, stream=True)
        resp.raise_for_status()
        chunks = []
        for raw in resp.iter_lines():
            if not raw:
                continue
            chunk = json.loads(raw)
            chunks.append(chunk.get("message", {}).get("content", ""))
            if chunk.get("done"):
                break
        return "".join(chunks)

    def stream(self, prompt: str, system: Optional[str] = None) -> Generator[str, None, None]:
        """Streaming chat. Yields tokens as they arrive."""
        if self._use_raw:
            resp = self._post_raw(system, prompt, stream=True)
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw:
                    continue
                chunk = json.loads(raw)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
            return

        resp = self._post_chat(system, prompt, stream=True)
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            chunk = json.loads(raw)
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
            if chunk.get("done"):
                break

    def parse_to_json(self, content: str, schema_hint: str = "") -> dict:
        """
        Parse unstructured DERIVED-OK content into JSON.
        Input must be PUBLIC or DERIVED-OK — never pass PRIVATE content here.
        """
        system = (
            "You are a data parser. Extract the requested fields and return "
            "valid JSON only. No explanation. No markdown fences."
        )
        hint   = f"\nExpected fields: {schema_hint}" if schema_hint else ""
        prompt = f"Parse this into JSON:{hint}\n\n{content}"
        raw    = self.chat(prompt, system=system).strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        return json.loads(raw.strip())

    def summarise(self, content: str, max_words: int = 80) -> str:
        """
        Produce a short DERIVED-OK summary of table or metric output.
        Input must be PUBLIC or DERIVED-OK — never pass PRIVATE content here.
        """
        system = (
            f"Summarise in under {max_words} words. "
            "State only facts present in the input. No interpretation."
        )
        return self.chat(content, system=system)

    def is_available(self) -> bool:
        """Check Ollama server is reachable and the configured model is loaded."""
        try:
            resp   = requests.get(f"{self.host}/api/tags", timeout=(3, 5))
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False


if __name__ == "__main__":
    llm = LocalLLM()
    print(f"[ollama_client] host={llm.host}  model={llm.model}")

    if not llm.is_available():
        print(f"[ollama_client] FAIL — model '{llm.model}' not available at {llm.host}")
        print("[ollama_client] To install: ollama pull qwen2.5:0.5b")
        print("[ollama_client] To use a different model: CRUCIBLE_LOCAL_MODEL=<name> python -m crucible.hybrid.ollama_client")
        raise SystemExit(1)

    print("[ollama_client] model available — running smoke test...")

    test_table = "steps_detected: 20\ncadence_hz: 1.8\nstance_pct: 62"
    print("\n[test 1] parse_to_json:")
    result = llm.parse_to_json(test_table, schema_hint="steps_detected, cadence_hz, stance_pct")
    print(json.dumps(result, indent=2))

    print("\n[test 2] stream summarise:")
    for token in llm.stream("Summarise in one sentence: steps=20, cadence=1.8 Hz, stance=62%"):
        print(token, end="", flush=True)
    print()

    print("\n[ollama_client] smoke test PASS")
