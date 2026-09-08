# Demo Logistics Agent — Multi-Agent Logistics Operations on WSO2 Agent Manager

A production-shaped, fully synthetic logistics demo built for **WSO2 Agent Manager / AMP**.

This repository demonstrates how multiple AI agents can collaborate over a shared operational system of record while preserving clear business responsibilities, human approval boundaries, API governance, and deterministic demo behavior.

The implementation follows the same practical pattern as the working [`demo-sdlc-agent`](https://github.com/joaokuntzwso2/demo-sdlc-agent): **FastAPI**, **LangGraph ReAct agents**, **LangChain/OpenAI**, WSO2-governed `OPENAI_URL` / `OPENAI_API_KEY`, and Agent Manager auto-instrumentation.

> **Synthetic demo data only.** All companies, people, shipment numbers, operational events, facilities, commitments, costs, and recovery scenarios in this repository are fictional.

---

## What this demo shows

A severe weather disruption at the **São Paulo / Guarulhos (GRU)** air gateway affects multiple shipments with different service commitments and business criticality.

Three specialized agents collaborate over the same mutable Logistics Core:

1. **Customer Experience Agent** — answers customer/order/tracking questions, explains ETA/SLA impact, opens cases, and queues customer notifications.
2. **Shipment Exception Manager** — investigates shipment exceptions, compares recovery options, recommends corrective action, and executes only explicitly approved recovery actions.
3. **Network Control Tower Agent** — analyzes disruption-wide impact, ranks affected shipments, calculates recommended recovery spend, and exposes event-driven operational APIs.

A fourth deployable component, **Logistics Core Mock**, acts as the shared in-memory system of record for customers, orders, shipments, tracking events, disruptions, cases, notifications, and recovery actions.

---

## Architecture

```text
                                      ┌───────────────────────────────┐
                                      │     Governed OpenAI / LLM     │
                                      │      via WSO2 Agent Manager   │
                                      └───────────────┬───────────────┘
                                                      │
                          ┌───────────────────────────┼───────────────────────────┐
                          │                           │                           │
                          ▼                           ▼                           ▼
                ┌──────────────────┐        ┌──────────────────┐       ┌────────────────────┐
                │ Customer         │        │ Shipment         │       │ Network Control    │
                │ Experience Agent │        │ Exception Agent  │       │ Tower Agent        │
                │                  │        │                  │       │                    │
                │ Chat Agent       │        │ Chat Agent       │       │ Custom API Agent   │
                │ POST /chat       │        │ POST /chat       │       │ /disruptions/...   │
                └─────────┬────────┘        └─────────┬────────┘       └──────────┬─────────┘
                          │                           │                           │
                          └───────────────────────────┼───────────────────────────┘
                                                      │ HTTP / X-API-Key
                                                      ▼
                                           ┌───────────────────────┐
                                           │ Logistics Core Mock   │
                                           │                       │
                                           │ Customers             │
                                           │ Orders                │
                                           │ Shipments             │
                                           │ Tracking Events       │
                                           │ SLA Commitments       │
                                           │ Disruptions           │
                                           │ Recovery Options      │
                                           │ Cases / Notifications │
                                           │ Recovery Actions      │
                                           └───────────────────────┘
```

### Why the Core is a separate service

If each deployed agent imported the same Python dictionary, each Agent Manager workload/pod would get its **own independent in-memory copy**. A recovery action executed by the exception agent would therefore not be visible to the customer agent.

`mock_core` solves that while keeping the demo self-contained: one service owns the mutable in-memory state, and every agent calls it over HTTP.

That is closer to a real logistics architecture, where agents would consume TMS, OMS, WMS, CRM, tracking, and carrier APIs rather than sharing process memory.

---

## Demo scenario

### Network disruption

```text
Disruption ID: DISR-GRU-0908
Facility:      GRU — São Paulo / Guarulhos air gateway
Cause:         Severe convective weather and reduced ramp / air capacity
Date:          2026-09-08
```

### Impacted shipments

| Tracking | Customer | Service | Destination | Initial SLA impact | Priority | Recommended action |
|---|---|---|---|---:|---|---|
| `BRX-784512` | Atlas Medical Supplies Brasil | Priority Air | Recife | 15h30 late | P1 | Reroute via VCP |
| `BRX-784533` | Lumina Electronics Brasil | Priority Air | Salvador | 3h15 late | P2 | Reroute via CNF |
| `BRX-784540` | VerdeMart Retail | Economy Air | Brasília | Still inside SLA | P4 | Wait for planned capacity |

A fourth shipment, `BRX-784566`, is healthy and out for delivery in Porto Alegre.

### Showcase recovery

For Atlas Medical shipment `BRX-784512`:

```text
Before recovery
---------------
Promised delivery: 2026-09-08 18:00 BRT
Current ETA:       2026-09-09 09:30 BRT
Projected miss:    930 minutes / 15h30

Recommended recovery
--------------------
Option:             REC-ATL-VCP
Action:             GRU → VCP transfer + protected VCP → REC capacity
Incremental cost:   BRL 1,850
New ETA:            2026-09-08 21:40 BRT
Projected miss:     220 minutes / 3h40
```

The demo intentionally demonstrates that **not every delayed shipment should receive premium recovery capacity**. Priority combines SLA exposure, service level, customer tier, cargo criticality, operational feasibility, and incremental cost.

---

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── Dockerfile
├── .env.example
├── logistics_common/
│   ├── chat_app.py            # Shared WSO2 /chat runtime + LangGraph execution
│   ├── config.py              # Governed/direct OpenAI configuration
│   └── core_client.py         # HTTP client for Logistics Core
├── mock_core/
│   ├── data.py                # Deterministic synthetic logistics dataset
│   ├── store.py               # Thread-safe in-memory state + business logic
│   ├── app.py                 # FastAPI system-of-record facade
│   ├── main.py
│   └── openapi.yaml
├── agents/
│   ├── customer_service/
│   │   ├── prompt.py
│   │   ├── tools.py
│   │   ├── app.py
│   │   └── main.py
│   ├── exception_manager/
│   │   ├── prompt.py
│   │   ├── tools.py
│   │   ├── app.py
│   │   └── main.py
│   └── control_tower/
│       ├── app.py
│       ├── main.py
│       └── openapi.yaml
└── tests/
    ├── conftest.py
    ├── test_core_api.py
    └── test_store.py
```

---

# Quick start — local development

## Prerequisites

- macOS or Linux
- Python 3.11+
- `pip`
- OpenAI API key only for LLM-backed chat tests

Clone the repository:

```bash
git clone https://github.com/joaokuntzwso2/demo-logistics-agent.git
cd demo-logistics-agent
```

Create a Python environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the deterministic tests:

```bash
pytest -q
```

Expected result:

```text
8 passed
```

---

## Run all components locally

All Agent Manager workloads use port `8000` by default. For local development, run each application on a different port:

| Port | Application |
|---:|---|
| `8010` | Logistics Core Mock |
| `8001` | Customer Experience Agent |
| `8002` | Shipment Exception Manager |
| `8003` | Network Control Tower Agent |

### Terminal 1 — Logistics Core

```bash
source .venv/bin/activate
PORT=8010 python -m mock_core.main
```

Verify:

```bash
curl -s http://localhost:8010/health | python -m json.tool
curl -s http://localhost:8010/demo/scenario | python -m json.tool
```

Swagger UI:

```text
http://localhost:8010/docs
```

### Terminal 2 — Customer Experience Agent

For local direct OpenAI access, use `OPENAI_API_KEY_DEFAULT`. Do **not** set `OPENAI_URL` locally unless you intentionally want to call a compatible gateway.

```bash
source .venv/bin/activate
export LOGISTICS_CORE_URL=http://localhost:8010
export OPENAI_API_KEY_DEFAULT=<your-openai-key>
export OPENAI_MODEL=gpt-4o
PORT=8001 python -m agents.customer_service.main
```

### Terminal 3 — Shipment Exception Manager

```bash
source .venv/bin/activate
export LOGISTICS_CORE_URL=http://localhost:8010
export OPENAI_API_KEY_DEFAULT=<your-openai-key>
export OPENAI_MODEL=gpt-4o
PORT=8002 python -m agents.exception_manager.main
```

### Terminal 4 — Network Control Tower

The Control Tower supports deterministic operation with `use_llm: false`, so an OpenAI key is optional for the first smoke test.

```bash
source .venv/bin/activate
export LOGISTICS_CORE_URL=http://localhost:8010
PORT=8003 python -m agents.control_tower.main
```

Verify deterministic analysis:

```bash
curl -s -X POST http://localhost:8003/disruptions/analyze \
  -H 'Content-Type: application/json' \
  -d '{"disruption_id":"DISR-GRU-0908","use_llm":false}' \
  | python -m json.tool
```

---

# Deploying on WSO2 Agent Manager / AMP

Use the **same repository and branch for all four registrations**.

```text
Repository:   https://github.com/joaokuntzwso2/demo-logistics-agent
Branch:       main
Project Path: /
Python:       3.11
```

Deploy **Logistics Core first**, because every functional agent depends on it.

## 1 — Logistics Core Mock

| Agent Manager field | Value |
|---|---|
| Name | `TransNova Logistics Core Mock` |
| Agent type | `Custom API Agent` |
| Build type | Python |
| Python | `3.11` |
| Start command | `python -m mock_core.main` |
| Port | `8000` |
| OpenAPI Spec Path | `mock_core/openapi.yaml` |
| Auto Instrumentation | Optional / ON is fine |

After deployment, copy the Core invoke/base URL.

If endpoint API-key security is enabled, create a credential such as:

```text
logistics-agent-clients
```

The three functional agents use:

```text
LOGISTICS_CORE_URL=<deployed Core base/invoke URL>
LOGISTICS_CORE_API_KEY=<Core API key>
```

Mark `LOGISTICS_CORE_API_KEY` as a secret.

---

## 2 — Customer Experience Agent

| Agent Manager field | Value |
|---|---|
| Name | `TransNova Customer Experience` |
| Agent type | `Chat Agent` |
| Start command | `python -m agents.customer_service.main` |
| Auto Instrumentation | `ON` |

Attach the OpenAI LLM Service Provider and keep the injected environment-variable names:

```text
OPENAI_URL
OPENAI_API_KEY
```

Add:

```text
OPENAI_MODEL=gpt-4o
LOGISTICS_CORE_URL=<Core base/invoke URL>
LOGISTICS_CORE_API_KEY=<Core API key>
```

---

## 3 — Shipment Exception Manager

| Agent Manager field | Value |
|---|---|
| Name | `TransNova Shipment Exception Manager` |
| Agent type | `Chat Agent` |
| Start command | `python -m agents.exception_manager.main` |
| Auto Instrumentation | `ON` |

Use the same LLM and Logistics Core configuration as the Customer Experience Agent.

---

## 4 — Network Control Tower Agent

| Agent Manager field | Value |
|---|---|
| Name | `TransNova Network Control Tower` |
| Agent type | `Custom API Agent` |
| Start command | `python -m agents.control_tower.main` |
| Port | `8000` |
| OpenAPI Spec Path | `agents/control_tower/openapi.yaml` |
| Auto Instrumentation | `ON` |

Use the same LLM and Logistics Core configuration.

---

# Environment variables

| Variable | Used by | Required | Description |
|---|---|---|---|
| `PORT` | All services | No | Runtime port. Defaults to `8000`. |
| `OPENAI_MODEL` | Functional agents | No | Model name. Defaults to `gpt-4o`. |
| `OPENAI_URL` | Functional agents | Governed mode | Injected by Agent Manager from the attached LLM Service Provider. |
| `OPENAI_API_KEY` | Functional agents | Governed mode | Injected gateway credential. |
| `OPENAI_API_KEY_DEFAULT` | Functional agents | Local direct mode only | Direct OpenAI credential used when `OPENAI_URL` is absent. |
| `LOGISTICS_CORE_URL` | Functional agents | Yes | Base URL of Logistics Core. Local default is `http://localhost:8010`. |
| `LOGISTICS_CORE_API_KEY` | Functional agents | When Core is secured | Sent as `X-API-Key`. Store as a secret. |
| `LOGISTICS_CORE_TIMEOUT_SECONDS` | Functional agents | No | Core HTTP timeout. Defaults to `8`. |

### Governed WSO2 LLM flow

```text
Agent
  │
  │ OPENAI_URL + OPENAI_API_KEY injected by Agent Manager
  ▼
WSO2 governed LLM / AI Gateway
  │
  ▼
OpenAI
```

The application deliberately does **not** pin its own Traceloop package. Keep Agent Manager Python Auto Instrumentation enabled and let AMP own the supported observability dependency set.

---

# API surface

## Logistics Core Mock

OpenAPI specification:

```text
mock_core/openapi.yaml
```

Key endpoints:

```text
GET  /health
GET  /demo/scenario
POST /demo/reset
GET  /demo/state

GET  /customers
GET  /customers/{customer_id}
GET  /customers/{customer_id}/orders
GET  /orders/{order_id}

GET  /shipments/{tracking_number}
GET  /shipments/{tracking_number}/events
GET  /shipments/{tracking_number}/sla
GET  /shipments/{tracking_number}/recovery-options
POST /shipments/{tracking_number}/cases
POST /shipments/{tracking_number}/notifications
POST /shipments/{tracking_number}/recovery

GET  /exceptions
GET  /disruptions
GET  /disruptions/{disruption_id}
GET  /disruptions/{disruption_id}/impact
```

## Chat Agent contract

Both Chat Agents expose:

```http
POST /chat
Content-Type: application/json
```

Request:

```json
{
  "message": "Where is BRX-784512 and are we meeting SLA?",
  "session_id": "demo-cx-1",
  "context": {}
}
```

Response:

```json
{
  "response": "..."
}
```

They also expose:

```text
GET /health
```

## Network Control Tower

OpenAPI specification:

```text
agents/control_tower/openapi.yaml
```

Endpoints:

```text
GET  /health
POST /disruptions/analyze
GET  /disruptions/{disruption_id}/impact
POST /recoveries/execute
```

Deterministic disruption analysis:

```json
{
  "disruption_id": "DISR-GRU-0908",
  "use_llm": false
}
```

With LLM-generated executive summary:

```json
{
  "disruption_id": "DISR-GRU-0908",
  "use_llm": true
}
```

---

# End-to-end customer demo runbook

Reset the demo before every presentation:

```http
POST /demo/reset
```

This restores the original shipment ETA, tracking history, cases, notifications, and recovery actions.

## Act 1 — Customer asks about an urgent medical shipment

Open **TransNova Customer Experience** and ask:

> Atlas Medical is calling about order ORD-ATL-1007. Where is it, what happened, and are we still meeting the promised delivery?

Expected behavior:

- Finds order `ORD-ATL-1007` and shipment `BRX-784512`.
- Identifies the GRU weather/capacity exception.
- Distinguishes promised delivery from current ETA.
- Reports the projected 15h30 SLA miss.

Then ask:

> Open a customer case and queue an email telling Atlas that operations is evaluating recovery options. Do not promise a new delivery time yet.

This creates shared mutable state in Logistics Core.

---

## Act 2 — Operations investigates the same shipment

Open **TransNova Shipment Exception Manager** and ask:

> Investigate BRX-784512. Compare every recovery option and recommend what operations should do. Do not execute anything yet.

Expected comparison:

```text
WAIT AT GRU
Cost: BRL 0
ETA: 2026-09-09 09:30 BRT
Projected miss: 15h30

REROUTE VIA VCP
Cost: BRL 1,850
ETA: 2026-09-08 21:40 BRT
Projected miss: 3h40
```

The agent should recommend `REC-ATL-VCP` but **not execute it** without explicit approval.

Then provide human approval:

> Approved. Execute REC-ATL-VCP for BRX-784512. Approved by Ana Ribeiro, approval reference APPROVED-GRU-0908-01.

Expected mutation:

- ETA changes to `2026-09-08T21:40:00-03:00`.
- Recovery state becomes `executed`.
- `RECOVERY_BOOKED` is appended to the tracking history.
- Approver, approval reference, and BRL 1,850 cost are recorded.

---

## Act 3 — Customer agent sees the change immediately

Return to **TransNova Customer Experience**:

> Give me the latest status for BRX-784512 now. Did anything change since the case was opened?

The Customer Experience Agent now sees the recovery performed by the Shipment Exception Manager because both agents read the same Logistics Core state.

Then ask:

> Queue an updated email to Atlas with the confirmed recovery plan and new ETA. Keep it concise and do not claim we are on time.

This is the strongest multi-agent moment in the demo: **one agent changes operational state; another agent immediately consumes the new state without being manually synchronized.**

---

## Act 4 — Network-wide control tower

Call:

```http
POST /disruptions/analyze
```

with:

```json
{
  "disruption_id": "DISR-GRU-0908",
  "use_llm": true
}
```

The deterministic ranking is designed to produce:

```text
1. BRX-784512 — P1 — Atlas Medical
2. BRX-784533 — P2 — Lumina Electronics
3. BRX-784540 — P4 — VerdeMart Retail
```

Before recovery actions, recommended incremental recovery spend is:

```text
BRL 2,530
```

This shows that the control tower optimizes disruption response across the network instead of treating every shipment independently.

---

# Useful demo prompts

## Customer Experience

```text
Track BRX-784566 and tell me whether it is healthy.
```

```text
List the orders for customer CUS-ATL-001.
```

```text
Explain the last four tracking events for BRX-784512 in customer-friendly language.
```

```text
What is the current SLA impact for BRX-784533?
```

## Shipment Exception Manager

```text
Which active network disruption is affecting BRX-784512?
```

```text
Compare recovery for BRX-784533. Is the BRL 680 reroute justified?
```

```text
Show me all shipments impacted by DISR-GRU-0908, prioritized by action urgency.
```

```text
Why should BRX-784540 wait rather than receive premium recovery capacity?
```

## Network Control Tower

Use `/disruptions/analyze` with `use_llm: false` first to prove deterministic business logic without an LLM dependency. Then repeat with `use_llm: true` to demonstrate a governed model creating an operational brief from the exact same source data.

---

# Testing

The automated tests validate the deterministic business behavior that the demo depends on:

- Atlas Medical starts with a critical projected SLA breach.
- GRU disruption priority is P1 → P2 → P4.
- Approved recovery mutates the shared ETA and tracking history.
- Customer-case creation is idempotent for an existing open case.
- Demo reset restores original state.
- Core API health, tracking, SLA, and recovery endpoints behave as expected.

Run:

```bash
pytest -q
```

---

# Observability story

For the three functional agents, keep **Python Auto Instrumentation** enabled in Agent Manager.

The application code intentionally keeps observability out of the business dependency graph. This avoids pin conflicts and allows AMP to inject the supported instrumentation stack.

A customer demo can therefore show:

```text
Agent invocation
  ↓
LLM call
  ↓
LangGraph reasoning / tool selection
  ↓
Logistics Core API calls
  ↓
Operational result
```

without requiring custom tracing code in each agent.

---

# Security and human-in-the-loop boundaries

The demo deliberately separates **recommendation** from **execution**.

Recovery execution requires explicit fields:

```text
approved_by
approval_reference
```

The Shipment Exception Manager is instructed to recommend recovery first and only mutate shipment state after explicit approval.

For deployed environments:

- Keep secrets in Agent Manager environment-secret configuration.
- Do not commit OpenAI credentials or Core API keys.
- Use API-key protection or another appropriate platform security policy for Custom API agents.
- Treat the mock Core as demo-only; it has no persistent database or production authentication model of its own.

---

# Production realism vs. deliberate simplifications

## Realistic patterns represented

- Customer, order, shipment, tracking, SLA, disruption, and recovery are separate concepts.
- Promised delivery and predicted/current ETA are distinct.
- Operational exceptions use structured codes and event history.
- A network disruption can affect many shipments differently.
- Recovery options include feasibility, ETA, incremental cost, and operational impact.
- Shipment priority considers more than lateness.
- Human approval is required before recovery mutation.
- Customer communication is separate from operational action.
- Multiple agents operate against a common system-of-record API.
- Deterministic logic remains available when the LLM is unavailable.

## Deliberate demo simplifications

- State is in memory and resets on Core restart.
- No real TMS, WMS, OMS, CRM, ERP, airline, carrier, or last-mile integration is used.
- No live geospatial routing, customs, dangerous-goods, driver-hours, warehouse slotting, duty/tax, or carrier-capacity optimization is performed.
- ETA and recovery alternatives are deterministic fixtures rather than predictive models.
- The Core is single-process; production implementations require durable transactional storage and concurrency controls appropriate to the source systems.

These constraints are intentional. The repository demonstrates **agent architecture and operational workflow**, not a production transportation-management algorithm.

---

# Resetting the demo

At any time:

```bash
curl -s -X POST http://localhost:8010/demo/reset | python -m json.tool
```

or invoke `POST /demo/reset` from the deployed Logistics Core API test console.

This makes the demo repeatable across customer sessions.

---

# Troubleshooting

## Agent health reports Logistics Core as unreachable

Check:

```text
LOGISTICS_CORE_URL
LOGISTICS_CORE_API_KEY
```

For local execution, use:

```text
LOGISTICS_CORE_URL=http://localhost:8010
```

For Agent Manager, use the deployed Core invoke/base URL, not `localhost`.

## Chat Agent starts but LLM calls fail locally

Set:

```text
OPENAI_API_KEY_DEFAULT=<direct OpenAI API key>
```

Do not set `OPENAI_URL` unless you are intentionally using a compatible governed gateway.

## Agent Manager LLM mode

Attach the LLM Service Provider and use the injected names:

```text
OPENAI_URL
OPENAI_API_KEY
```

Do not hard-code the upstream OpenAI credential into the repository.

## Control Tower without OpenAI

Use:

```json
{
  "disruption_id": "DISR-GRU-0908",
  "use_llm": false
}
```

The endpoint will return deterministic ranking and recovery-cost data without an LLM call.

## Need a clean demo after executing recovery

Call:

```http
POST /demo/reset
```

---

## Repository

```text
https://github.com/joaokuntzwso2/demo-logistics-agent
```

Designed as a repeatable customer demo for multi-agent logistics operations on WSO2 Agent Manager / AMP.
