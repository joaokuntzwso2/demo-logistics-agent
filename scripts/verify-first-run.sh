#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "==> Python syntax"
python3 -m compileall -q agents logistics_common mock_core tests

echo "==> Tests"
python3 -m pytest -q

echo "==> Port policy"
python3 - <<'PY'
import os
from logistics_common.runtime import chat_agent_port, custom_api_port
os.environ["PORT"] = "8080"
assert chat_agent_port() == 8000
assert custom_api_port() == 8080
print("Chat Agents: 8000 ✓")
print("Custom API default: 8080 ✓")
PY

echo "==> Entrypoints"
grep -n "chat_agent_port" agents/customer_service/main.py agents/exception_manager/main.py
grep -n "custom_api_port" mock_core/main.py agents/control_tower/main.py

echo "==> No committed secrets"
if git grep -nE 'sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY_DEFAULT=.+' -- ':!*.md' ':!.env.example'; then
  echo "ERROR: Possible secret-like value found. Review before committing." >&2
  exit 1
else
  echo "No obvious OpenAI key found ✓"
fi

echo "==> Git diff"
git status --short
git diff --check
git diff --stat

echo
echo "READY TO REVIEW. Run: git diff"
