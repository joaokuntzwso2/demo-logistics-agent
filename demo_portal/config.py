from __future__ import annotations

import os
from dataclasses import dataclass


def _value(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip().rstrip("/")


@dataclass(frozen=True)
class ServiceTarget:
    name: str
    url: str
    api_key: str
    kind: str

    @property
    def configured(self) -> bool:
        return bool(self.url)


@dataclass(frozen=True)
class PortalSettings:
    core: ServiceTarget
    customer: ServiceTarget
    exception: ServiceTarget
    control_tower: ServiceTarget
    request_timeout_seconds: float
    portal_port: int


def load_settings() -> PortalSettings:
    return PortalSettings(
        core=ServiceTarget(
            name="Logistics Core",
            url=_value("PORTAL_CORE_URL", _value("LOGISTICS_CORE_URL", "http://localhost:8010")),
            api_key=_value("PORTAL_CORE_API_KEY", os.getenv("LOGISTICS_CORE_API_KEY", "")),
            kind="mock-core",
        ),
        customer=ServiceTarget(
            name="Customer Experience",
            url=_value("PORTAL_CUSTOMER_AGENT_URL", "http://localhost:8001"),
            api_key=_value("PORTAL_CUSTOMER_AGENT_API_KEY"),
            kind="chat-agent",
        ),
        exception=ServiceTarget(
            name="Shipment Exception Manager",
            url=_value("PORTAL_EXCEPTION_AGENT_URL", "http://localhost:8002"),
            api_key=_value("PORTAL_EXCEPTION_AGENT_API_KEY"),
            kind="chat-agent",
        ),
        control_tower=ServiceTarget(
            name="Network Control Tower",
            url=_value("PORTAL_CONTROL_TOWER_URL", "http://localhost:8003"),
            api_key=_value("PORTAL_CONTROL_TOWER_API_KEY"),
            kind="custom-api-agent",
        ),
        request_timeout_seconds=float(os.getenv("PORTAL_REQUEST_TIMEOUT_SECONDS", "45")),
        portal_port=int(os.getenv("PORTAL_PORT", "8090")),
    )
