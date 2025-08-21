#!/bin/bash
# Back2Task LLM Server Setup Script
# OpenAI gpt-oss-20b を vLLM で起動

set -e

# 色付きメッセージ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 Back2Task LLM Server Setup${NC}"
echo "================================"

# デフォルト設定
MODEL_NAME="openai/gpt-oss-20b"
PORT=8000
MAX_MODEL_LEN=32768
QUANTIZATION=""
DEVICE="auto"

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --max-len)
            MAX_MODEL_LEN="$2"
            shift 2
            ;;
        --quantization)
            QUANTIZATION="$2"
            shift 2
            ;;
        --cpu)
            DEVICE="cpu"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model MODEL_NAME     Model to use (default: openai/gpt-oss-20b)"
            echo "  --port PORT           Port to run on (default: 8000)"
            echo "  --max-len LENGTH      Max model length (default: 32768)"
            echo "  --quantization TYPE   Quantization type (awq, gptq, etc.)"
            echo "  --cpu                 Force CPU inference"
            echo "  --help                Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}設定:${NC}"
echo "  モデル: $MODEL_NAME"
echo "  ポート: $PORT"
echo "  最大長: $MAX_MODEL_LEN"
echo "  デバイス: $DEVICE"
if [[ -n "$QUANTIZATION" ]]; then
    echo "  量子化: $QUANTIZATION"
fi
echo ""

# Python 環境チェック
echo -e "${BLUE}🔍 環境チェック${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 が見つかりません${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version)${NC}"

# GPU チェック
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✅ NVIDIA GPU 検出:${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -3
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  NVIDIA GPU が検出されませんでした${NC}"
    echo -e "${YELLOW}   CPU推論を使用します（低速）${NC}"
    GPU_AVAILABLE=false
    DEVICE="cpu"
fi

# vLLM 環境セットアップ
VLLM_ENV="$HOME/venv/vllm"

echo -e "\n${BLUE}🛠️  vLLM 環境セットアップ${NC}"

if [[ ! -d "$VLLM_ENV" ]]; then
    echo "vLLM用Python環境を作成中..."
    python3 -m venv "$VLLM_ENV"
fi

echo "vLLM環境をアクティベート中..."
source "$VLLM_ENV/bin/activate"

echo "vLLMをインストール中..."
pip install --upgrade pip

if [[ "$GPU_AVAILABLE" == "true" ]]; then
    # GPU版
    pip install vllm>=0.5.0
else
    # CPU版
    pip install vllm>=0.5.0 --extra-index-url https://download.pytorch.org/whl/cpu
fi

echo -e "${GREEN}✅ vLLM インストール完了${NC}"

# モデルダウンロード確認
echo -e "\n${BLUE}📦 モデル準備${NC}"

python3 -c "
from huggingface_hub import snapshot_download
import os

model_name = '$MODEL_NAME'
print(f'モデル {model_name} の可用性をチェック中...')

try:
    # モデル情報を取得（ダウンロードはしない）
    from transformers import AutoConfig
    config = AutoConfig.from_pretrained(model_name)
    print(f'✅ モデル {model_name} が利用可能です')
    print(f'   パラメータ数: {config.num_parameters if hasattr(config, \"num_parameters\") else \"不明\"}')
    print(f'   隠れ層サイズ: {config.hidden_size if hasattr(config, \"hidden_size\") else \"不明\"}')
except Exception as e:
    print(f'❌ モデル {model_name} の取得に失敗: {e}')
    print('利用可能な代替モデル:')
    print('  - microsoft/DialoGPT-large')
    print('  - EleutherAI/gpt-neo-2.7B')
    print('  - EleutherAI/gpt-j-6b')
    exit(1)
"

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ モデル準備失敗${NC}"
    exit 1
fi

# vLLM サーバー起動コマンド構築
VLLM_CMD="python -m vllm.entrypoints.openai.api_server"
VLLM_CMD="$VLLM_CMD --model $MODEL_NAME"
VLLM_CMD="$VLLM_CMD --served-model-name gpt-oss-20b"
VLLM_CMD="$VLLM_CMD --port $PORT"
VLLM_CMD="$VLLM_CMD --max-model-len $MAX_MODEL_LEN"

if [[ -n "$QUANTIZATION" ]]; then
    VLLM_CMD="$VLLM_CMD --quantization $QUANTIZATION"
fi

if [[ "$DEVICE" == "cpu" ]]; then
    VLLM_CMD="$VLLM_CMD --enforce-eager"
    # CPU推論の場合は低いコンテキスト長を推奨
    if [[ "$MAX_MODEL_LEN" -gt 16384 ]]; then
        echo -e "${YELLOW}⚠️  CPU推論では低いmax-model-lenを推奨します${NC}"
        VLLM_CMD=$(echo "$VLLM_CMD" | sed "s/--max-model-len $MAX_MODEL_LEN/--max-model-len 8192/")
    fi
fi

echo -e "\n${BLUE}🚀 vLLM サーバー起動${NC}"
echo -e "${YELLOW}コマンド:${NC} $VLLM_CMD"
echo ""
echo -e "${GREEN}サーバーを起動しています...${NC}"
echo -e "${YELLOW}終了するには Ctrl+C を押してください${NC}"
echo ""

# ログファイル設定
LOG_FILE="$HOME/.cache/back2task/vllm.log"
mkdir -p "$(dirname "$LOG_FILE")"

# サーバー起動
echo "ログファイル: $LOG_FILE"
echo "API エンドポイント: http://localhost:$PORT"
echo "モデル名: gpt-oss-20b"
echo ""

# tmux セッション起動（利用可能な場合）
if command -v tmux &> /dev/null; then
    echo -e "${BLUE}💡 tmux セッション 'back2task-llm' で起動します${NC}"
    echo "   セッションにアタッチ: tmux attach -t back2task-llm"
    echo "   セッション一覧: tmux list-sessions"
    echo ""
    
    tmux new-session -d -s back2task-llm "
        source '$VLLM_ENV/bin/activate'
        echo '🤖 Back2Task LLM Server'
        echo 'モデル: $MODEL_NAME'
        echo 'ポート: $PORT'
        echo 'ログ: $LOG_FILE'
        echo ''
        $VLLM_CMD 2>&1 | tee '$LOG_FILE'
    "
    
    echo -e "${GREEN}✅ vLLM サーバーがバックグラウンドで起動しました${NC}"
    echo ""
    echo "接続テスト:"
    echo "  curl http://localhost:$PORT/v1/models"
    echo ""
    echo "Back2Task API での使用:"
    echo "  LLM_URL=http://localhost:$PORT python api/main.py"
    
else
    # tmux が利用できない場合は直接起動
    exec $VLLM_CMD 2>&1 | tee "$LOG_FILE"
fi