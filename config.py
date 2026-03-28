from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def env_str(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower().strip()

# Where to persist Chroma indexes (per-session subfolder is created)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

