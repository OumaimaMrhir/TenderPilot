"""Client LLM optionnel (OpenAI ou Anthropic).

Sans clé API, les agents fonctionnent en mode « règles » : déterministe, gratuit,
et utilisé par les tests et la CI.
"""

from __future__ import annotations

import json
import os
import re

import httpx


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str) -> None:
        self.provider, self.api_key, self.model = provider, api_key, model

    @classmethod
    def from_env(cls) -> LLMClient | None:
        provider = os.getenv("LLM_PROVIDER", "").lower()
        if provider == "openai" and os.getenv("OPENAI_API_KEY"):
            return cls("openai", os.environ["OPENAI_API_KEY"], os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            return cls("anthropic", os.environ["ANTHROPIC_API_KEY"], os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"))
        return None

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        if self.provider == "openai":
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        response.raise_for_status()
        return "".join(p.get("text", "") for p in response.json()["content"] if p.get("type") == "text")

    def complete_json(self, system: str, prompt: str) -> object:
        raw = self.complete(system + "\nRéponds uniquement avec du JSON valide, sans texte autour.", prompt)
        match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
        if not match:
            raise ValueError("Le LLM n'a pas renvoyé de JSON exploitable.")
        return json.loads(match.group(1))
