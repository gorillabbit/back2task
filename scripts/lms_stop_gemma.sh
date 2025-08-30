#!/usr/bin/env bash
# Unload the model defined in .env.local and stop LM Studio Local Server via lms

set -e

# Move to project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

if ! command -v lms >/dev/null 2>&1; then
  echo "[ERROR] 'lms' CLI not found in PATH."
  exit 1
fi

# Load required env
if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
else
  echo "[ERROR] .env.local not found at project root: $ROOT_DIR"
  exit 1
fi

if [[ -z "${LLM_MODEL:-}" ]]; then
  echo "[ERROR] LLM_MODEL is not set in .env.local"
  exit 1
fi

echo "[INFO] Unloading model: ${LLM_MODEL} (best-effort)"
lms unload "${LLM_MODEL}" || true

echo "[INFO] Stopping LM Studio Local Server..."
lms server stop
echo "[OK] Stopped."
