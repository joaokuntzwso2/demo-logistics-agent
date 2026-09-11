"""HTTP client for the shared mock Logistics Core API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class LogisticsCoreError(RuntimeError):
    pass


class LogisticsCoreClient:
    def __init__(self) -> None:
        self.base_url = (os.getenv("LOGISTICS_CORE_URL") or "http://localhost:8010").rstrip("/")
        self.api_key = (os.getenv("LOGISTICS_CORE_API_KEY") or "").strip()
        self.host_header = (os.getenv("LOGISTICS_CORE_HOST_HEADER") or "").strip()
        self.timeout = float(os.getenv("LOGISTICS_CORE_TIMEOUT_SECONDS", "8"))

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        # AMP local gateway uses virtual-host routing.
        # Inside Kubernetes, *.localhost resolves to loopback by design,
        # so workloads call host.k3d.internal while preserving the
        # gateway hostname in the HTTP Host header.
        if self.host_header:
            headers["Host"] = self.host_header

        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
                response = client.request(method, f"{self.base_url}{path}", **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LogisticsCoreError(
                f"Logistics Core returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LogisticsCoreError(f"Could not reach Logistics Core at {self.base_url}: {exc}") from exc

    def health(self): return self._request("GET", "/health")
    def scenario(self): return self._request("GET", "/demo/scenario")
    def catalog(self): return self._request("GET", "/demo/catalog")
    def customer(self, customer_id: str): return self._request("GET", f"/customers/{customer_id}")
    def customer_orders(self, customer_id: str): return self._request("GET", f"/customers/{customer_id}/orders")
    def order(self, order_id: str): return self._request("GET", f"/orders/{order_id}")
    def shipment(self, tracking: str): return self._request("GET", f"/shipments/{tracking}")
    def events(self, tracking: str): return self._request("GET", f"/shipments/{tracking}/events")
    def sla(self, tracking: str): return self._request("GET", f"/shipments/{tracking}/sla")
    def recovery_options(self, tracking: str): return self._request("GET", f"/shipments/{tracking}/recovery-options")
    def exceptions(self): return self._request("GET", "/exceptions")
    def disruptions(self): return self._request("GET", "/disruptions")
    def disruption(self, disruption_id: str): return self._request("GET", f"/disruptions/{disruption_id}")
    def disruption_impact(self, disruption_id: str): return self._request("GET", f"/disruptions/{disruption_id}/impact")

    def create_case(self, tracking: str, reason: str, owner: str = "Customer Care"):
        return self._request("POST", f"/shipments/{tracking}/cases", json={"reason": reason, "owner": owner})

    def notify(self, tracking: str, channel: str, message: str):
        return self._request(
            "POST", f"/shipments/{tracking}/notifications", json={"channel": channel, "message": message}
        )

    def execute_recovery(self, tracking: str, option_id: str, approved_by: str, approval_reference: str | None = None):
        return self._request(
            "POST",
            f"/shipments/{tracking}/recovery",
            json={
                "option_id": option_id,
                "approved_by": approved_by,
                "approval_reference": approval_reference,
            },
        )


CORE = LogisticsCoreClient()
