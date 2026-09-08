from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from logistics_common.core_client import CORE


@tool
def get_shipment_exception_context(tracking_number: str) -> dict[str, Any]:
    """Get full shipment/order/customer context for a specific exception shipment."""
    shipment = CORE.shipment(tracking_number)
    shipment["sla"] = CORE.sla(tracking_number)
    shipment["events"] = CORE.events(tracking_number)["events"]
    return shipment


@tool
def get_recovery_options(tracking_number: str) -> dict[str, Any]:
    """Get deterministic recovery options, cost, capacity, new ETA, risk and recommendation for a shipment."""
    return CORE.recovery_options(tracking_number)


@tool
def get_active_network_disruptions() -> dict[str, Any]:
    """List active network disruptions affecting the logistics network."""
    return CORE.disruptions()


@tool
def get_disruption_impact(disruption_id: str) -> dict[str, Any]:
    """Get all shipments impacted by a disruption, ranked by operational priority and SLA risk."""
    return CORE.disruption_impact(disruption_id)


@tool
def open_operations_case(tracking_number: str, reason: str) -> dict[str, Any]:
    """Open an operations exception case for a shipment."""
    return CORE.create_case(tracking_number, reason, owner="Shipment Exception Desk")


@tool
def execute_approved_recovery(
    tracking_number: str,
    option_id: str,
    approved_by: str,
    approval_reference: str,
) -> dict[str, Any]:
    """Execute a recovery option after explicit human approval. Requires approver name and approval reference from the user."""
    if not approval_reference or len(approval_reference.strip()) < 4:
        raise ValueError("An explicit approval_reference is required to execute a recovery action.")
    return CORE.execute_recovery(tracking_number, option_id, approved_by, approval_reference)


@tool
def queue_operational_customer_notification(tracking_number: str, message: str) -> dict[str, Any]:
    """Queue a customer email notification after an operational decision is confirmed."""
    return CORE.notify(tracking_number, "email", message)


LANGCHAIN_TOOLS = [
    get_shipment_exception_context,
    get_recovery_options,
    get_active_network_disruptions,
    get_disruption_impact,
    open_operations_case,
    execute_approved_recovery,
    queue_operational_customer_notification,
]
