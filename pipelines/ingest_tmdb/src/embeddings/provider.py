from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class EmbeddingProvider(Protocol):
    def dimension(self) -> int: ...
    def embed_text(self, text: str) -> list[float]: ...


@dataclass
class OllamaEmbeddingProvider:
    base_url: str
    model: str
    timeout_s: float = 60.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.strip().rstrip("/")
        if not self.base_url:
            raise ValueError(
                "OLLAMA_BASE_URL is empty. Set it to http://localhost:11434 or your Ollama host."
            )
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError(
                "OLLAMA_BASE_URL must start with http:// or https://"
            )
        self._client = httpx.Client(timeout=self.timeout_s)

    def dimension(self) -> int:
        # cache the dimension after first call
        if not hasattr(self, "_dim"):
            v = self.embed_text("dimension probe")
            self._dim = len(v)
        return self._dim

    def embed_text(self, text: str) -> list[float]:
        r = self._client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        r.raise_for_status()
        return r.json()["embedding"]


@dataclass
class BedrockEmbeddingProvider:
    region: str
    model_id: str
    dimensions: int = 1024
    normalize: bool = True

    def __post_init__(self) -> None:
        import boto3
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    def dimension(self) -> int:
        return self.dimensions

    def embed_text(self, text: str) -> list[float]:
        body = json.dumps(
            {"inputText": text, "normalize": self.normalize, "dimensions": self.dimensions}
        )
        resp = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        payload = json.loads(resp["body"].read())
        return payload["embedding"]
