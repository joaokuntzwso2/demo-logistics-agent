"""Mock Logistics Core API.

This service is deliberately not an LLM agent. It is a deterministic in-memory
system-of-record façade that all demo agents share. Deploy it as a Custom API
Agent in WSO2 Agent Manager so the other agents observe the same mutable state.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .store import STORE

app = FastAPI(
    title="TransNova Logistics Core Mock API",
    version="1.0.0",
    description="Deterministic in-memory customer/order/shipment/tracking data for the logistics multi-agent demo.",
)


class CaseRequest(BaseModel):
    reason: str = Field(..., min_length=3)
    owner: str = "Customer Care"


class NotificationRequest(BaseModel):
    channel: str = Field(default="email", pattern="^(email|sms|whatsapp)$")
    message: str = Field(..., min_length=3)


class RecoveryRequest(BaseModel):
    option_id: str
    approved_by: str = Field(..., min_length=2)
    approval_reference: str | None = None


@app.get("/health")
def health():
    return STORE.health()


@app.get("/demo/scenario")
def scenario():
    return STORE.scenario()


@app.post("/demo/reset")
def reset():
    return STORE.reset()


@app.get("/demo/state")
def state_summary():
    return STORE.state_summary()


@app.get("/customers")
def customers():
    return {"customers": STORE.list_customers()}


@app.get("/customers/{customer_id}")
def customer(customer_id: str):
    result = STORE.get_customer(customer_id)
    if not result:
        raise HTTPException(404, "Customer not found")
    return result


@app.get("/customers/{customer_id}/orders")
def customer_orders(customer_id: str):
    if not STORE.get_customer(customer_id):
        raise HTTPException(404, "Customer not found")
    return {"customer_id": customer_id, "orders": STORE.customer_orders(customer_id)}


@app.get("/orders/{order_id}")
def order(order_id: str):
    result = STORE.get_order(order_id)
    if not result:
        raise HTTPException(404, "Order not found")
    return result


@app.get("/shipments/{tracking_number}")
def shipment(tracking_number: str):
    result = STORE.get_shipment(tracking_number)
    if not result:
        raise HTTPException(404, "Shipment not found")
    return result


@app.get("/shipments/{tracking_number}/events")
def shipment_events(tracking_number: str):
    result = STORE.tracking_events(tracking_number)
    if result is None:
        raise HTTPException(404, "Shipment not found")
    return {"tracking_number": tracking_number, "events": result}


@app.get("/shipments/{tracking_number}/sla")
def shipment_sla(tracking_number: str):
    result = STORE.sla(tracking_number)
    if not result:
        raise HTTPException(404, "Shipment not found")
    return result


@app.get("/shipments/{tracking_number}/recovery-options")
def shipment_recovery_options(tracking_number: str):
    result = STORE.recovery_options(tracking_number)
    if result is None:
        raise HTTPException(404, "Shipment not found")
    return {"tracking_number": tracking_number, "options": result}


@app.post("/shipments/{tracking_number}/cases")
def create_case(tracking_number: str, req: CaseRequest):
    result = STORE.create_case(tracking_number, req.reason, req.owner)
    if not result:
        raise HTTPException(404, "Shipment not found")
    return result


@app.post("/shipments/{tracking_number}/notifications")
def create_notification(tracking_number: str, req: NotificationRequest):
    result = STORE.create_notification(tracking_number, req.channel, req.message)
    if not result:
        raise HTTPException(404, "Shipment not found")
    return result


@app.post("/shipments/{tracking_number}/recovery")
def execute_recovery(tracking_number: str, req: RecoveryRequest):
    try:
        result = STORE.execute_recovery(
            tracking_number,
            req.option_id,
            req.approved_by,
            req.approval_reference,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not result:
        raise HTTPException(404, "Shipment not found")
    return result


@app.get("/exceptions")
def exceptions():
    return {"exceptions": STORE.list_exceptions()}


@app.get("/disruptions")
def disruptions(active_only: bool = Query(default=True)):
    return {"disruptions": STORE.list_disruptions(active_only=active_only)}


@app.get("/disruptions/{disruption_id}")
def disruption(disruption_id: str):
    result = STORE.get_disruption(disruption_id)
    if not result:
        raise HTTPException(404, "Disruption not found")
    return result


@app.get("/disruptions/{disruption_id}/impact")
def disruption_impact(disruption_id: str):
    ranked = STORE.impacted_ranked(disruption_id)
    if ranked is None:
        raise HTTPException(404, "Disruption not found")
    return {"disruption_id": disruption_id, "impacted_shipments": ranked}
