from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests

from .models import ProviderName


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str


class LLMClient(Protocol):
    provider: str
    model: str

    def chat(self, messages: list[dict[str, str]]) -> LLMResult:
        ...


class ProviderConfigError(RuntimeError):
    pass


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()


class NimClient:
    provider = "nim"

    def __init__(self) -> None:
        self.base_url = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.api_key = os.environ.get("NIM_API_KEY", "")
        self.model = os.environ.get("NIM_MODEL", "mistralai/ministral-14b-instruct-2512")
        self.timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))

    def chat(self, messages: list[dict[str, str]]) -> LLMResult:
        if not self.api_key:
            raise ProviderConfigError("NIM_API_KEY is not set. Choose Ollama or add your NVIDIA NIM API key.")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": self.max_tokens,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return LLMResult(content=content, provider=self.provider, model=self.model)


class OllamaClient:
    provider = "ollama"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "90"))

    def chat(self, messages: list[dict[str, str]]) -> LLMResult:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["message"]["content"]
        return LLMResult(content=content, provider=self.provider, model=self.model)


def get_default_provider() -> ProviderName:
    value = os.environ.get("LLM_PROVIDER", "nim").lower()
    if value in {"nim", "ollama"}:
        return value  # type: ignore[return-value]
    return "nim"


def get_client(provider: ProviderName | None = None) -> LLMClient:
    selected = provider or get_default_provider()
    if selected == "ollama":
        return OllamaClient()
    return NimClient()


def provider_health() -> dict[str, dict[str, object]]:
    nim = NimClient()
    ollama = OllamaClient()
    return {
        "nim": {
            "configured": bool(nim.api_key),
            "model": nim.model,
            "base_url": nim.base_url,
        },
        "ollama": {
            "configured": True,
            "model": ollama.model,
            "base_url": ollama.base_url,
        },
    }
