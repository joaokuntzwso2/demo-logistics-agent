"""Event-driven Network Control Tower agent exposed as a Custom API Agent."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from logistics_common.config import OPENAI_MODEL, llm_health, resolve_llm_config
from logistics_common.core_client import CORE, LogisticsCoreError

log = logging.getLogger("transnova-control-tower")

SYSTEM_PROMPT = """
You are the TransNova Network Control Tower Agent for a fictional logistics company.
You receive structured disruption and shipment-impact data from the deterministic Logistics Core.

Your task is to produce an operations-leadership brief. The supplied JSON is the source of truth.
Do not invent shipments, capacity, costs, ETAs, customer commitments, or actions.
Do not claim access to real transport systems.

Prioritize:
1. safety and feasibility,
2. customer/service criticality,
3. SLA protection,
4. network capacity,
5. incremental recovery spend.

Return a concise brief with:
- disruption status,
- number of impacted shipments,
- P1/P2 items first,
- recommended recovery per priority shipment,
- total incremental cost of recommended actions,
- explicit approvals/communications required,
- what can safely wait.
"""


class AnalyzeDisruptionRequest(BaseModel):
    disruption_id: str = "DISR-GRU-0908"
    use_llm: bool = True


class ExecuteRecoveryRequest(BaseModel):
    tracking_number: str
    option_id: str
    approved_by: str = Field(..., min_length=2)
    approval_reference: str = Field(..., min_length=4)
    notify_customer: bool = False
    notification_message: str | None = None


class ControlTowerResponse(BaseModel):
    disruption_id: str
    summary: str
    data: dict[str, Any]


def _deterministic_summary(disruption: dict[str, Any], impact: list[dict[str, Any]]) -> str:
    p1 = [x for x in impact if x["priority"] == "P1"]
    p2 = [x for x in impact if x["priority"] == "P2"]
    sla_risk = [x for x in impact if x["sla"]["sla_at_risk"]]
    recommended = [x["recommended_recovery"] for x in impact if x.get("recommended_recovery")]
    cost = sum(float(x.get("incremental_cost_brl", 0)) for x in recommended)
    top = impact[0] if impact else None
    top_text = (
        f" Highest priority is {top['tracking_number']} ({top['priority']}) for {top['customer']}."
        if top else ""
    )
    return (
        f"{disruption['severity'].upper()} disruption {disruption['disruption_id']} at {disruption['facility_name']} "
        f"affects {len(impact)} shipment(s); {len(sla_risk)} currently project an SLA miss. "
        f"Priority mix: {len(p1)} P1, {len(p2)} P2. Recommended recovery spend is BRL {cost:,.2f}."
        f"{top_text}"
    )


def _llm_summary(payload: dict[str, Any]) -> str:
    llm = ChatOpenAI(model=OPENAI_MODEL, **resolve_llm_config())
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="Produce the control-tower brief from this deterministic demo data:\n" + json.dumps(payload, indent=2)),
        ]
    )
    return str(result.content).strip()


def ready_payload() -> dict[str, Any]:
    core_reachable = False
    core_error = None
    try:
        core_reachable = bool(CORE.health().get("ok"))
    except Exception as exc:
        core_error = str(exc)
    return {
        "ok": True,
        "name": "transnova-network-control-tower",
        "port": int(os.getenv("PORT", "8000")),
        "llm": llm_health(),
        "logistics_core": {"url": CORE.base_url, "api_key_set": bool(CORE.api_key), "reachable": core_reachable, "error": core_error},
        "interface": "custom-api",
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("READY %s", json.dumps(ready_payload()))
    yield


app = FastAPI(
    title="TransNova Network Control Tower Agent",
    version="1.0.0",
    description="Custom API agent for disruption triage, prioritization and approved recovery execution.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/health")
def health():
    return ready_payload()


@app.post("/disruptions/analyze", response_model=ControlTowerResponse)
def analyze_disruption(req: AnalyzeDisruptionRequest):
    try:
        disruption = CORE.disruption(req.disruption_id)
        impact_response = CORE.disruption_impact(req.disruption_id)
    except LogisticsCoreError as exc:
        raise HTTPException(502, str(exc)) from exc

    impact = impact_response["impacted_shipments"]
    payload = {
        "disruption": disruption,
        "ranked_impact": impact,
        "recommended_action_cost_brl": sum(
            float(row.get("recommended_recovery", {}).get("incremental_cost_brl", 0))
            for row in impact
            if row.get("recommended_recovery")
        ),
    }
    summary = _deterministic_summary(disruption, impact)
    if req.use_llm:
        try:
            summary = _llm_summary(payload)
        except Exception as exc:
            log.warning("LLM summary failed; using deterministic summary: %s", exc)

    return ControlTowerResponse(disruption_id=req.disruption_id, summary=summary, data=payload)


@app.post("/recoveries/execute")
def execute_recovery(req: ExecuteRecoveryRequest):
    try:
        result = CORE.execute_recovery(
            req.tracking_number,
            req.option_id,
            req.approved_by,
            req.approval_reference,
        )
        notification = None
        if req.notify_customer:
            message = req.notification_message or (
                f"A recovery plan has been confirmed for shipment {req.tracking_number}. "
                f"The current estimated delivery is {result['shipment']['estimated_delivery']}."
            )
            notification = CORE.notify(req.tracking_number, "email", message)
        return {"recovery": result, "notification": notification}
    except LogisticsCoreError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/disruptions/{disruption_id}/impact")
def get_impact(disruption_id: str):
    try:
        return CORE.disruption_impact(disruption_id)
    except LogisticsCoreError as exc:
        raise HTTPException(502, str(exc)) from exc
