from __future__ import annotations

import os
from dotenv import load_dotenv

from embeddings.provider import (
    BedrockEmbeddingProvider,
    OllamaEmbeddingProvider,
    EmbeddingProvider,
)

def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def make_provider() -> EmbeddingProvider:
    # load repo root .env
    from pathlib import Path
    root = Path(__file__).resolve().parents[4]
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local", override=True)
    load_dotenv(Path.cwd() / ".env", override=True)
    load_dotenv(Path.cwd() / ".env.local", override=True)

    provider = _env_or_default("EMBEDDINGS_PROVIDER", "ollama").lower()

    if provider == "ollama":
        base_url = _env_or_default("OLLAMA_BASE_URL", "http://localhost:11434")
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.hostname == "ollama":
            base_url = "http://localhost:11434"
        return OllamaEmbeddingProvider(
            base_url=base_url,
            model=_env_or_default("OLLAMA_MODEL", "nomic-embed-text"),
            timeout_s=float(_env_or_default("EMBED_TIMEOUT_S", "60")),
        )

    if provider == "bedrock":
        return BedrockEmbeddingProvider(
            region=os.getenv("AWS_REGION", "eu-west-1"),
            model_id=os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"),
            dimensions=int(os.getenv("EMBEDDING_DIM", "1024")),
            normalize=os.getenv("BEDROCK_NORMALIZE", "1") == "1",
        )

    raise ValueError(f"Unknown EMBEDDINGS_PROVIDER={provider}")
