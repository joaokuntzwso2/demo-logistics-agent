from __future__ import annotations

import os

CHAT_AGENT_PORT = 8000
CUSTOM_API_DEFAULT_PORT = 8080


def chat_agent_port() -> int:
    """WSO2 Agent Manager Chat Agents always listen on port 8000."""
    return CHAT_AGENT_PORT


def custom_api_port() -> int:
    """Custom API Agents use the port configured by Agent Manager."""
    return int(os.getenv("PORT", str(CUSTOM_API_DEFAULT_PORT)))
