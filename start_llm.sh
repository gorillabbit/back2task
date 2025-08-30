#!/bin/bash
# Start LM Studio local server via CLI
# Requires LM Studio CLI to be installed and accessible as `lmstudio` or via LMSTUDIO_CLI env var.

set -e

CLI=${LMSTUDIO_CLI:-lmstudio}
MODEL=${LLM_MODEL:-google/gemma-3-4b}
PORT=${LLM_PORT:-1234}
HOST=${LLM_HOST:-127.0.0.1}
LOG_DIR="/tmp/back2task"
LOG_FILE="$LOG_DIR/llm.log"

mkdir -p "$LOG_DIR"

echo "🚀 Starting LM Studio server (model: $MODEL, port: $PORT)..."

if ! command -v "$CLI" >/dev/null 2>&1; then
    echo "❌ LM Studio CLI '$CLI' not found. Set LMSTUDIO_CLI or install LM Studio CLI."
    exit 1
fi

nohup "$CLI" start --model "$MODEL" --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
LLM_PID=$!
echo "$LLM_PID" > "$LOG_DIR/llm.pid"

echo "✅ LM Studio server started (PID: $LLM_PID)"
echo "   Logs: $LOG_FILE"
