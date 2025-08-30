#!/usr/bin/env bash
# Start Gemma via LM Studio CLI (lms)
# Usage: bash scripts/lms_start_gemma.sh
# Requires: .env.local with LLM_URL and LLM_MODEL

set -e

# Resolve project root (one level up from this script)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

# Load shared env
if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
else
  echo "[ERROR] .env.local not found at project root: $ROOT_DIR"
  echo "        Copy .env.local.example to .env.local and set required values."
  exit 1
fi

# Determine model strictly from .env.local (no args override)
if [[ -z "${LLM_MODEL:-}" ]]; then
  echo "[ERROR] LLM_MODEL is not set. Define it in .env.local"
  exit 1
fi
MODEL="$LLM_MODEL"

# Require LLM_URL from .env.local
if [[ -z "${LLM_URL:-}" ]]; then
  echo "[ERROR] LLM_URL is not set. Define it in .env.local"
  exit 1
fi

if ! command -v lms >/dev/null 2>&1; then
  echo "[ERROR] 'lms' CLI not found. Install LM Studio and ensure 'lms' is in PATH."
  echo "        https://lmstudio.ai/"
  exit 1
fi

echo "[INFO] Checking if model is already loaded via 'lms ps'..."
if lms ps 2>/dev/null | grep -qi -- "${MODEL}"; then
  echo "[OK] '${MODEL}' already loaded. Skipping 'lms load'."
else
  echo "[INFO] Loading model: ${MODEL}"
  lms load "${MODEL}"
fi

echo "[INFO] Ensuring LM Studio Local Server at ${LLM_URL}"
if curl -s "${LLM_URL}/v1/models" > /dev/null 2>&1; then
  echo "[OK] Server already running."
else
  lms server start
fi

echo "[INFO] Waiting for server to respond..."
ATTEMPTS=60
until curl -s "${LLM_URL}/v1/models" > /dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  if [[ $ATTEMPTS -le 0 ]]; then
    echo "[ERROR] Could not reach ${LLM_URL}/v1/models"
    exit 1
  fi
  sleep 1
  printf "."
done
echo
echo "[OK] Server is up. /v1/models response:"
curl -s "${LLM_URL}/v1/models" || true
echo
