from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .client import PortalGateway, PortalUpstreamError
from .config import load_settings

SETTINGS = load_settings()
PORTAL = PortalGateway(SETTINGS)
STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class AnalyzeRequest(BaseModel):
    disruption_id: str = "DISR-GRU-0908"
    use_llm: bool = True


class MockLookupRequest(BaseModel):
    resource: Literal[
        "catalog",
        "state",
        "scenario",
        "customers",
        "disruptions",
        "exceptions",
    ]


def _public_target(target) -> dict[str, Any]:
    return {
        "name": target.name,
        "url": target.url,
        "configured": target.configured,
        "api_key_configured": bool(target.api_key),
        "kind": target.kind,
    }


async def _safe(coro, fallback=None):
    try:
        return await coro
    except Exception as exc:
        return fallback if fallback is not None else {"error": str(exc)}


app = FastAPI(
    title="TransNova Logistics AI Operations Portal",
    version="1.0.0",
    description="Professional demo UI orchestrating the TransNova Agent Manager logistics scenario.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status():
    health = await PORTAL.all_health()
    return {
        "services": {
            "core": _public_target(SETTINGS.core),
            "customer": _public_target(SETTINGS.customer),
            "exception": _public_target(SETTINGS.exception),
            "control_tower": _public_target(SETTINGS.control_tower),
        },
        "health": health,
    }


@app.get("/api/bootstrap")
async def bootstrap():
    scenario, disruption, impact, state, catalog, health = await asyncio.gather(
        _safe(PORTAL.request(SETTINGS.core, "GET", "/demo/scenario")),
        _safe(PORTAL.request(SETTINGS.core, "GET", "/disruptions/DISR-GRU-0908")),
        _safe(PORTAL.request(SETTINGS.core, "GET", "/disruptions/DISR-GRU-0908/impact")),
        _safe(PORTAL.request(SETTINGS.core, "GET", "/demo/state")),
        _safe(PORTAL.request(SETTINGS.core, "GET", "/demo/catalog")),
        PORTAL.all_health(),
    )
    return {
        "scenario": scenario,
        "disruption": disruption,
        "impact": impact,
        "mutable_state": state,
        "catalog": catalog,
        "health": health,
    }


@app.post("/api/story/reset")
async def reset_story():
    try:
        return await PORTAL.request(SETTINGS.core, "POST", "/demo/reset")
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/agents/customer/chat")
async def customer_chat(req: ChatRequest):
    try:
        return await PORTAL.chat(SETTINGS.customer, req.message, req.session_id)
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/agents/exception/chat")
async def exception_chat(req: ChatRequest):
    try:
        return await PORTAL.chat(SETTINGS.exception, req.message, req.session_id)
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/agents/control-tower/analyze")
async def control_tower_analyze(req: AnalyzeRequest):
    try:
        return await PORTAL.request(
            SETTINGS.control_tower,
            "POST",
            "/disruptions/analyze",
            json=req.model_dump(),
        )
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/mock/catalog")
async def mock_catalog():
    try:
        return await PORTAL.request(SETTINGS.core, "GET", "/demo/catalog")
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/mock/state")
async def mock_state():
    try:
        return await PORTAL.request(SETTINGS.core, "GET", "/demo/state")
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/mock/shipment/{tracking_number}")
async def mock_shipment(tracking_number: str):
    try:
        shipment, events, sla, options = await asyncio.gather(
            PORTAL.request(SETTINGS.core, "GET", f"/shipments/{tracking_number}"),
            PORTAL.request(SETTINGS.core, "GET", f"/shipments/{tracking_number}/events"),
            PORTAL.request(SETTINGS.core, "GET", f"/shipments/{tracking_number}/sla"),
            PORTAL.request(SETTINGS.core, "GET", f"/shipments/{tracking_number}/recovery-options"),
        )
        return {"shipment": shipment, "events": events, "sla": sla, "recovery_options": options}
    except PortalUpstreamError as exc:
        raise HTTPException(502, str(exc)) from exc
