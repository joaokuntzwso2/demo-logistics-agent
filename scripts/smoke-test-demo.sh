#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if [[ ! -f .env.portal ]]; then
  echo "ERROR: .env.portal not found. Copy .env.portal.example and configure it first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.portal
set +a

fail=0
TMP_DIR="${TMPDIR:-/tmp}/transnova-smoke-$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

need_var() {
  name="$1"
  eval "value=\${$name:-}"
  if [[ -z "$value" ]]; then
    echo "✗ $name is empty"
    fail=1
  else
    echo "✓ $name configured"
  fi
}

for v in \
  PORTAL_CORE_URL PORTAL_CORE_API_KEY \
  PORTAL_CUSTOMER_AGENT_URL PORTAL_CUSTOMER_AGENT_API_KEY \
  PORTAL_EXCEPTION_AGENT_URL PORTAL_EXCEPTION_AGENT_API_KEY \
  PORTAL_CONTROL_TOWER_URL PORTAL_CONTROL_TOWER_API_KEY; do
  need_var "$v"
done

[[ "$fail" -eq 0 ]] || exit 1

echo
printf '%s\n' '--- Direct gateway checks ---'

request() {
  label="$1"; method="$2"; url="$3"; key="$4"; body="${5:-}"; outfile="$6"
  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$outfile" -w '%{http_code}' -X "$method" \
      -H 'Content-Type: application/json' \
      -H "X-API-Key: $key" \
      -d "$body" "$url" || true)"
  else
    code="$(curl -sS -o "$outfile" -w '%{http_code}' -X "$method" \
      -H "X-API-Key: $key" "$url" || true)"
  fi
  if [[ "$code" == "200" ]]; then
    echo "✓ $label -> HTTP 200"
  else
    echo "✗ $label -> HTTP ${code:-curl-error}"
    if [[ -s "$outfile" ]]; then
      python3 - <<PY 2>/dev/null || head -c 500 "$outfile" || true
import json
p = "$outfile"
try:
    d=json.load(open(p))
    print(json.dumps(d, indent=2)[:800])
except Exception:
    print(open(p, errors='replace').read()[:800])
PY
    fi
    fail=1
  fi
}

request "Logistics Core catalog" GET \
  "$PORTAL_CORE_URL/demo/catalog" "$PORTAL_CORE_API_KEY" "" "$TMP_DIR/core.json"

if [[ -s "$TMP_DIR/core.json" ]]; then
  python3 - "$TMP_DIR/core.json" <<'PY' || fail=1
import json, sys
p=sys.argv[1]
data=json.load(open(p))
assert data.get("mocked") is True, "catalog.mocked must be true"
assert data.get("scenario", {}).get("showcase_tracking") == "BRX-784512"
assert "BRX-784512" in data.get("shipments", {})
print("✓ Core deterministic scenario verified")
PY
fi

request "Customer Experience /chat" POST \
  "$PORTAL_CUSTOMER_AGENT_URL/chat" "$PORTAL_CUSTOMER_AGENT_API_KEY" \
  '{"message":"For readiness validation only: give me the current status of order ORD-ATL-1007 in one concise paragraph. Do not create a case or notification.","session_id":"smoke-customer","context":{"surface":"smoke-test"}}' \
  "$TMP_DIR/customer.json"

request "Shipment Exception Manager /chat" POST \
  "$PORTAL_EXCEPTION_AGENT_URL/chat" "$PORTAL_EXCEPTION_AGENT_API_KEY" \
  '{"message":"For readiness validation only: investigate BRX-784512 and name the recommended recovery option. Do not execute anything.","session_id":"smoke-exception","context":{"surface":"smoke-test"}}' \
  "$TMP_DIR/exception.json"

request "Network Control Tower deterministic analysis" POST \
  "$PORTAL_CONTROL_TOWER_URL/disruptions/analyze" "$PORTAL_CONTROL_TOWER_API_KEY" \
  '{"disruption_id":"DISR-GRU-0908","use_llm":false}' \
  "$TMP_DIR/tower.json"

echo
printf '%s\n' '--- Repository safety checks ---'

if git ls-files .env.portal | grep -q .; then
  echo "✗ .env.portal is tracked by Git — remove it from Git immediately"
  fail=1
else
  echo "✓ .env.portal is not tracked"
fi

SECRET_SCAN_FILE="$(mktemp "${TMPDIR:-/tmp}/transnova-secret-scan.XXXXXX")"

python3 - "$SECRET_SCAN_FILE" <<'PYSCAN'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

out_path = Path(sys.argv[1])

portal_key = re.compile(
    r"PORTAL_(?:CORE|CUSTOMER_AGENT|EXCEPTION_AGENT|CONTROL_TOWER)_API_KEY\s*=\s*(.*)"
)
openai_key = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")

placeholder_values = {
    "",
    "...",
    "…",
    "your_key",
    "your_api_key",
    "api_key",
    "key",
    "replace_me",
    "changeme",
    "placeholder",
}

def is_placeholder(raw: str) -> bool:
    value = raw.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"', "`"}:
        value = value[1:-1].strip()

    low = value.lower()
    if low in placeholder_values:
        return True
    if re.fullmatch(r"<[^>]+>", value):
        return True
    if re.fullmatch(r"\$\{?[A-Z0-9_]+\}?", value):
        return True
    if low.startswith(("your_", "example_", "placeholder_", "replace_")):
        return True
    if value and set(value) <= {".", "…"}:
        return True
    return False

tracked = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
findings: list[str] = []

for item in tracked:
    if not item:
        continue
    rel = item.decode("utf-8", "surrogateescape")
    if rel in {".env.portal.example", "scripts/smoke-test-demo.sh"}:
        continue

    path = Path(rel)
    try:
        text = path.read_text(errors="replace")
    except (OSError, UnicodeError):
        continue

    for lineno, line in enumerate(text.splitlines(), 1):
        if openai_key.search(line):
            findings.append(f"{rel}:{lineno}:{line.strip()}")
            continue

        match = portal_key.search(line)
        if match and not is_placeholder(match.group(1)):
            findings.append(f"{rel}:{lineno}:{line.strip()}")

out_path.write_text("\n".join(findings) + ("\n" if findings else ""))
PYSCAN

if [[ -s "$SECRET_SCAN_FILE" ]]; then
  echo "✗ possible credential committed in tracked files:"
  cat "$SECRET_SCAN_FILE"
  rm -f "$SECRET_SCAN_FILE"
  fail=1
else
  rm -f "$SECRET_SCAN_FILE"
  echo "✓ no obvious committed portal/OpenAI credential found"
fi

if [[ "${PORTAL_URL:-http://localhost:${PORTAL_PORT:-8090}}" =~ ^http://localhost|^http://127\.0\.0\.1 ]]; then
  portal="${PORTAL_URL:-http://localhost:${PORTAL_PORT:-8090}}"
  code="$(curl -sS -o "$TMP_DIR/portal.json" -w '%{http_code}' "$portal/api/status" 2>/dev/null || true)"
  if [[ "$code" == "200" ]]; then
    echo "✓ Portal API reachable at $portal"
  else
    echo "• Portal is not currently running at $portal (not a failure for preflight)"
  fi
fi

echo
if [[ "$fail" -eq 0 ]]; then
  echo "READY: TransNova demo preflight passed."
  echo "Tip: POST /demo/reset before the customer demo to restore deterministic state."
else
  echo "FAILED: one or more preflight checks failed." >&2
  exit 1
fi
