"""Reusable WSO2 Agent Manager Chat Agent runtime."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from openai import APIError, RateLimitError
from pydantic import BaseModel, Field

from .config import OPENAI_MODEL, llm_health, resolve_llm_config
from .core_client import CORE
from .runtime import chat_agent_port

MAX_SESSION_MESSAGES = 40


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message for the agent.")
    session_id: str = Field(..., description="Client-provided conversation/session id.")
    context: dict[str, Any] | None = Field(default=None, description="Optional WSO2 Agent Manager context payload.")


class ChatResponse(BaseModel):
    response: str


def _final_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str):
                return msg.content.strip()
            if isinstance(msg.content, list):
                return "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in msg.content
                ).strip()
    return ""


def _truncate(history: list[BaseMessage]) -> list[BaseMessage]:
    if len(history) <= MAX_SESSION_MESSAGES:
        return history
    cut = len(history) - MAX_SESSION_MESSAGES
    while cut < len(history) and isinstance(history[cut], ToolMessage):
        cut += 1
    return history[cut:]


def create_chat_app(*, name: str, slug: str, description: str, system_prompt: str, tools: Sequence[Any]) -> FastAPI:
    log = logging.getLogger(slug)
    sessions: dict[str, list[BaseMessage]] = {}
    locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
    agent_box: dict[str, Any] = {"agent": None}

    def get_agent():
        if agent_box["agent"] is None:
            llm = ChatOpenAI(model=OPENAI_MODEL, **resolve_llm_config())
            agent_box["agent"] = create_react_agent(llm, tools=list(tools), prompt=system_prompt)
        return agent_box["agent"]

    def health_payload() -> dict[str, Any]:
        core_ok = False
        core_error = None
        try:
            core_ok = bool(CORE.health().get("ok"))
        except Exception as exc:  # health should remain safe even when dependency is down
            core_error = str(exc)
        return {
            "ok": True,
            "name": slug,
            "agent_display_name": name,
            "port": chat_agent_port(),
            "llm": llm_health(),
            "logistics_core": {
                "url": CORE.base_url,
                "api_key_set": bool(CORE.api_key),
                "reachable": core_ok,
                "error": core_error,
            },
            "endpoints": {"chat": "POST /chat", "health": "GET /health"},
        }

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log.info("READY %s", json.dumps(health_payload()))
        yield

    app = FastAPI(title=name, description=description, version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/health")
    def health():
        return health_payload()

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        if not req.message.strip():
            return ChatResponse(response="Please provide a logistics question or task.")

        sid = req.session_id or "_anonymous_"
        started = time.perf_counter()
        with locks[sid]:
            history = sessions.get(sid, []) + [HumanMessage(content=req.message)]
            if req.context:
                log.info("session=%s context=%s", sid, json.dumps(req.context)[:500])
            try:
                result = get_agent().invoke(
                    {"messages": history},
                    config={
                        "configurable": {"thread_id": sid},
                        "metadata": {"session_id": sid, "agent": slug},
                        "recursion_limit": 20,
                    },
                )
                history = result["messages"]
                reply = _final_text(history) or "I could not produce a logistics answer from the available data."
            except GraphRecursionError:
                log.warning("session=%s langgraph recursion limit exceeded", sid)
                reply = "The analysis loop reached its limit. Please narrow the request to one shipment, order, customer, or disruption."
            except (RateLimitError, APIError) as exc:
                log.warning("session=%s LLM error: %s", sid, exc)
                reply = "I could not reach the configured LLM provider. The logistics data service may still be available; please retry."
            except Exception as exc:  # defensive runtime path
                log.exception("session=%s unhandled error: %s", sid, exc)
                reply = f"I could not complete the logistics request: {exc}"

            sessions[sid] = _truncate(history)
            log.info(
                "session=%s reply_chars=%d elapsed_ms=%d",
                sid,
                len(reply),
                int((time.perf_counter() - started) * 1000),
            )
            return ChatResponse(response=reply)

    return app
