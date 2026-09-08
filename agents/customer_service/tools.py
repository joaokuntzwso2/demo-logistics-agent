from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from logistics_common.core_client import CORE


@tool
def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Get a logistics customer account profile, tier, SLA profile, contact and service notes."""
    return CORE.customer(customer_id)


@tool
def list_customer_orders(customer_id: str) -> dict[str, Any]:
    """List all demo orders for a customer account."""
    return CORE.customer_orders(customer_id)


@tool
def get_order_status(order_id: str) -> dict[str, Any]:
    """Get an order, its delivery commitment and linked shipment details."""
    return CORE.order(order_id)


@tool
def track_shipment(tracking_number: str) -> dict[str, Any]:
    """Get the current shipment status, location, ETA, exception and customer/order context."""
    return CORE.shipment(tracking_number)


@tool
def get_tracking_timeline(tracking_number: str) -> dict[str, Any]:
    """Get tracking events for a shipment in chronological order."""
    return CORE.events(tracking_number)


@tool
def get_delivery_commitment(tracking_number: str) -> dict[str, Any]:
    """Compare current ETA with the promised delivery time and return projected SLA risk."""
    return CORE.sla(tracking_number)


@tool
def open_customer_case(tracking_number: str, reason: str) -> dict[str, Any]:
    """Open or return an existing customer-care case for a shipment."""
    return CORE.create_case(tracking_number, reason, owner="Customer Experience")


@tool
def queue_customer_notification(tracking_number: str, channel: str, message: str) -> dict[str, Any]:
    """Queue a demo customer notification. Channel must be email, sms, or whatsapp."""
    return CORE.notify(tracking_number, channel, message)


LANGCHAIN_TOOLS = [
    get_customer_profile,
    list_customer_orders,
    get_order_status,
    track_shipment,
    get_tracking_timeline,
    get_delivery_commitment,
    open_customer_case,
    queue_customer_notification,
]
