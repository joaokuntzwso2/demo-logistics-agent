from __future__ import annotations

import os
from typing import Any

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o").strip()


def resolve_llm_config() -> dict[str, Any]:
    """Match the governed OpenAI pattern used by the working SDLC demo repo."""
    base_url = (os.getenv("OPENAI_URL") or "").strip()
    governed_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    byo_api_key = (os.getenv("OPENAI_API_KEY_DEFAULT") or "").strip()

    if base_url:
        return {
            "base_url": base_url,
            "api_key": governed_api_key or "missing-api-key",
            "default_headers": {
                "X-API-Key": governed_api_key,
                "API-Key": governed_api_key,
                "x-api-key": governed_api_key,
            },
        }
    return {"api_key": byo_api_key or "missing-api-key"}


def llm_health() -> dict[str, bool | str]:
    return {
        "model": OPENAI_MODEL,
        "governed": bool(os.getenv("OPENAI_URL")),
        "OPENAI_URL_set": bool(os.getenv("OPENAI_URL")),
        "OPENAI_API_KEY_set": bool(os.getenv("OPENAI_API_KEY")),
        "OPENAI_API_KEY_DEFAULT_set": bool(os.getenv("OPENAI_API_KEY_DEFAULT")),
    }
