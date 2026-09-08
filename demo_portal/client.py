from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import PortalSettings, ServiceTarget


class PortalUpstreamError(RuntimeError):
    pass


class PortalGateway:
    def __init__(self, settings: PortalSettings):
        self.settings = settings

    @staticmethod
    def _headers(target: ServiceTarget) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if target.api_key:
            headers["X-API-Key"] = target.api_key
        return headers

    async def request(
        self,
        target: ServiceTarget,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        if not target.configured:
            raise PortalUpstreamError(f"{target.name} is not configured")
        try:
            async with httpx.AsyncClient(
                timeout=timeout or self.settings.request_timeout_seconds,
                headers=self._headers(target),
            ) as client:
                response = await client.request(method, f"{target.url}{path}", json=json)
                response.raise_for_status()
                if not response.content:
                    return {"ok": True}
                return response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000]
            raise PortalUpstreamError(
                f"{target.name} returned HTTP {exc.response.status_code}: {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise PortalUpstreamError(f"Could not reach {target.name} at {target.url}: {exc}") from exc

    async def health(self, target: ServiceTarget) -> dict[str, Any]:
        try:
            data = await self.request(target, "GET", "/health", timeout=6)
            return {"ok": bool(data.get("ok", True)), "data": data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def all_health(self) -> dict[str, Any]:
        targets = {
            "core": self.settings.core,
            "customer": self.settings.customer,
            "exception": self.settings.exception,
            "control_tower": self.settings.control_tower,
        }
        values = await asyncio.gather(*(self.health(t) for t in targets.values()))
        return {key: value for key, value in zip(targets, values)}

    async def chat(self, target: ServiceTarget, message: str, session_id: str) -> dict[str, Any]:
        return await self.request(
            target,
            "POST",
            "/chat",
            json={"message": message, "session_id": session_id, "context": {"surface": "transnova-demo-portal"}},
        )
