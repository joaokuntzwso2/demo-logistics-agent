#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
if [[ -f .env.portal ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.portal
  set +a
fi
exec python3 -m demo_portal.main
