"""Thread-safe in-memory logistics store used by the mock Core API."""

from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from .data import DEMO_NOW, fresh_state


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _minutes_between(later: str, earlier: str) -> int:
    return int((_dt(later) - _dt(earlier)).total_seconds() // 60)


TIER_WEIGHT = {"platinum": 30, "gold": 20, "silver": 10, "bronze": 0}
CRITICALITY_WEIGHT = {"critical": 35, "high": 20, "normal": 5, "low": 0}
SERVICE_WEIGHT = {"Priority Air": 25, "Economy Air": 10, "Standard Road": 5}


class LogisticsStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = fresh_state()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._state = fresh_state()
            return {"ok": True, "reset_at": DEMO_NOW}

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "service": "transnova-logistics-core-mock",
                "demo_now": DEMO_NOW,
                "counts": {
                    "customers": len(self._state["customers"]),
                    "orders": len(self._state["orders"]),
                    "shipments": len(self._state["shipments"]),
                    "disruptions": len(self._state["disruptions"]),
                    "incidents": len(self._state["incidents"]),
                },
            }

    def scenario(self) -> dict[str, Any]:
        return {
            "company": "TransNova Logistics (fictional)",
            "scenario": "GRU severe-weather capacity disruption",
            "demo_now": DEMO_NOW,
            "primary_disruption": "DISR-GRU-0908",
            "showcase_tracking": "BRX-784512",
            "showcase_order": "ORD-ATL-1007",
            "showcase_customer": "CUS-ATL-001",
            "healthy_tracking": "BRX-784566",
        }

    def list_customers(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(list(self._state["customers"].values()))

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        with self._lock:
            obj = self._state["customers"].get(customer_id)
            return deepcopy(obj) if obj else None

    def customer_orders(self, customer_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(
                [o for o in self._state["orders"].values() if o["customer_id"] == customer_id]
            )

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            order = self._state["orders"].get(order_id)
            if not order:
                return None
            result = deepcopy(order)
            result["shipments"] = [
                deepcopy(self._state["shipments"][sid])
                for sid in order.get("shipment_ids", [])
                if sid in self._state["shipments"]
            ]
            return result

    def get_shipment(self, tracking: str) -> dict[str, Any] | None:
        with self._lock:
            shipment = self._state["shipments"].get(tracking)
            if not shipment:
                return None
            result = deepcopy(shipment)
            result["order"] = deepcopy(self._state["orders"].get(shipment["order_id"]))
            result["customer"] = deepcopy(self._state["customers"].get(shipment["customer_id"]))
            return result

    def tracking_events(self, tracking: str) -> list[dict[str, Any]] | None:
        with self._lock:
            if tracking not in self._state["shipments"]:
                return None
            return deepcopy(self._state["tracking_events"].get(tracking, []))

    def sla(self, tracking: str) -> dict[str, Any] | None:
        with self._lock:
            shipment = self._state["shipments"].get(tracking)
            if not shipment:
                return None
            delay = _minutes_between(shipment["estimated_delivery"], shipment["promised_delivery"])
            remaining_to_commit = _minutes_between(shipment["promised_delivery"], DEMO_NOW)
            return {
                "tracking_number": tracking,
                "promised_delivery": shipment["promised_delivery"],
                "estimated_delivery": shipment["estimated_delivery"],
                "projected_delay_minutes": max(delay, 0),
                "delivery_buffer_minutes": max(-delay, 0),
                "minutes_until_commitment": remaining_to_commit,
                "sla_at_risk": delay > 0,
                "sla_breached_projected": delay > 0,
                "severity": (
                    "critical" if delay > 720 else "high" if delay > 240 else "medium" if delay > 60 else "low" if delay > 0 else "none"
                ),
            }

    def list_exceptions(self) -> list[dict[str, Any]]:
        with self._lock:
            result = []
            for tracking, shipment in self._state["shipments"].items():
                if shipment["status"] != "exception":
                    continue
                context = self.get_shipment(tracking)
                context["sla"] = self.sla(tracking)
                result.append(context)
            return result

    def get_disruption(self, disruption_id: str) -> dict[str, Any] | None:
        with self._lock:
            disruption = self._state["disruptions"].get(disruption_id)
            if not disruption:
                return None
            result = deepcopy(disruption)
            result["shipments"] = [
                self.get_shipment(t) for t in disruption["impacted_shipments"] if t in self._state["shipments"]
            ]
            return result

    def list_disruptions(self, active_only: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._state["disruptions"].values())
            if active_only:
                items = [d for d in items if d["status"] == "active"]
            return deepcopy(items)

    def recovery_options(self, tracking: str) -> list[dict[str, Any]] | None:
        with self._lock:
            if tracking not in self._state["shipments"]:
                return None
            return deepcopy(self._state["recovery_options"].get(tracking, []))

    def priority_score(self, tracking: str) -> dict[str, Any] | None:
        with self._lock:
            shipment = self._state["shipments"].get(tracking)
            if not shipment:
                return None
            order = self._state["orders"][shipment["order_id"]]
            customer = self._state["customers"][shipment["customer_id"]]
            sla = self.sla(tracking)
            delay = sla["projected_delay_minutes"]
            delay_score = min(30, int(delay / 30)) if delay > 0 else 0
            score = (
                TIER_WEIGHT.get(customer["tier"], 0)
                + CRITICALITY_WEIGHT.get(order["business_criticality"], 0)
                + SERVICE_WEIGHT.get(shipment["service_level"], 0)
                + delay_score
            )
            if score >= 85:
                priority = "P1"
            elif score >= 60:
                priority = "P2"
            elif score >= 35:
                priority = "P3"
            else:
                priority = "P4"
            return {
                "tracking_number": tracking,
                "score": score,
                "priority": priority,
                "factors": {
                    "customer_tier": customer["tier"],
                    "business_criticality": order["business_criticality"],
                    "service_level": shipment["service_level"],
                    "projected_delay_minutes": delay,
                },
            }

    def impacted_ranked(self, disruption_id: str) -> list[dict[str, Any]] | None:
        with self._lock:
            disruption = self._state["disruptions"].get(disruption_id)
            if not disruption:
                return None
            rows = []
            for tracking in disruption["impacted_shipments"]:
                shipment = self.get_shipment(tracking)
                score = self.priority_score(tracking)
                options = self.recovery_options(tracking) or []
                recommended = next((o for o in options if o.get("recommended")), None)
                rows.append(
                    {
                        "tracking_number": tracking,
                        "customer": shipment["customer"]["name"],
                        "order_id": shipment["order_id"],
                        "service_level": shipment["service_level"],
                        "priority": score["priority"],
                        "priority_score": score["score"],
                        "sla": self.sla(tracking),
                        "recommended_recovery": recommended,
                    }
                )
            rows.sort(key=lambda x: x["priority_score"], reverse=True)
            return rows

    def create_case(self, tracking: str, reason: str, owner: str = "Customer Care") -> dict[str, Any] | None:
        with self._lock:
            if tracking not in self._state["shipments"]:
                return None
            existing = next(
                (
                    c
                    for c in self._state["cases"].values()
                    if c["tracking_number"] == tracking and c["status"] == "open"
                ),
                None,
            )
            if existing:
                return deepcopy(existing)
            case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
            case = {
                "case_id": case_id,
                "tracking_number": tracking,
                "status": "open",
                "owner": owner,
                "reason": reason,
                "created_at": DEMO_NOW,
            }
            self._state["cases"][case_id] = case
            return deepcopy(case)

    def create_notification(self, tracking: str, channel: str, message: str) -> dict[str, Any] | None:
        with self._lock:
            shipment = self._state["shipments"].get(tracking)
            if not shipment:
                return None
            notification = {
                "notification_id": f"NTF-{uuid.uuid4().hex[:8].upper()}",
                "tracking_number": tracking,
                "customer_id": shipment["customer_id"],
                "channel": channel,
                "message": message,
                "status": "queued",
                "created_at": DEMO_NOW,
            }
            self._state["notifications"].append(notification)
            return deepcopy(notification)

    def execute_recovery(
        self,
        tracking: str,
        option_id: str,
        approved_by: str,
        approval_reference: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            shipment = self._state["shipments"].get(tracking)
            if not shipment:
                return None
            options = self._state["recovery_options"].get(tracking, [])
            selected = next((o for o in options if o["option_id"] == option_id), None)
            if not selected:
                raise ValueError(f"Unknown recovery option {option_id} for {tracking}")
            if not selected.get("capacity_available"):
                raise ValueError(f"Recovery option {option_id} has no capacity available")

            shipment["estimated_delivery"] = selected["new_estimated_delivery"]
            shipment["recovery_status"] = "executed"
            shipment["selected_recovery_option"] = option_id
            shipment["substatus"] = "recovery_in_progress"
            shipment["last_event_at"] = DEMO_NOW

            event = {
                "timestamp": DEMO_NOW,
                "code": "RECOVERY_BOOKED",
                "location": shipment["current_location"],
                "description": f"Recovery option {option_id} executed: {selected['description']}",
            }
            self._state["tracking_events"].setdefault(tracking, []).append(event)

            action = {
                "action_id": f"ACT-{uuid.uuid4().hex[:8].upper()}",
                "tracking_number": tracking,
                "option_id": option_id,
                "approved_by": approved_by,
                "approval_reference": approval_reference,
                "incremental_cost_brl": selected["incremental_cost_brl"],
                "executed_at": DEMO_NOW,
                "new_estimated_delivery": selected["new_estimated_delivery"],
            }
            self._state["recovery_actions"].append(action)

            return {
                "ok": True,
                "action": deepcopy(action),
                "shipment": self.get_shipment(tracking),
                "sla": self.sla(tracking),
            }

    def state_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "cases": deepcopy(list(self._state["cases"].values())),
                "notifications": deepcopy(self._state["notifications"]),
                "recovery_actions": deepcopy(self._state["recovery_actions"]),
            }


STORE = LogisticsStore()
