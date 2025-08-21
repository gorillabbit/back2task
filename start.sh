#!/bin/bash
# Back2Task 一括起動スクリプト
set -e

# 色付きメッセージ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎯 Back2Task 起動中...${NC}"
echo "================================"

# プロジェクトルート取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 仮想環境確認
if [[ ! -d "venv" ]]; then
    echo -e "${YELLOW}⚠️  仮想環境が見つかりません。セットアップを実行中...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ 仮想環境が見つかりました${NC}"
fi

# 仮想環境をアクティベート
source venv/bin/activate

# PYTHONPATH設定
export PYTHONPATH="$SCRIPT_DIR"

# PIDファイルディレクトリ作成
mkdir -p /tmp/back2task

# 既存プロセス終了
echo -e "${YELLOW}🧹 既存プロセスをチェック中...${NC}"

# PIDファイルから既存プロセスを終了
if [[ -f "/tmp/back2task/api.pid" ]]; then
    API_PID=$(cat /tmp/back2task/api.pid)
    if ps -p "$API_PID" > /dev/null 2>&1; then
        echo "   既存APIサーバーを停止中 (PID: $API_PID)"
        kill "$API_PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f /tmp/back2task/api.pid
fi

if [[ -f "/tmp/back2task/pump.pid" ]]; then
    PUMP_PID=$(cat /tmp/back2task/pump.pid)
    if ps -p "$PUMP_PID" > /dev/null 2>&1; then
        echo "   既存Event Pumpを停止中 (PID: $PUMP_PID)"
        kill "$PUMP_PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f /tmp/back2task/pump.pid
fi

# ポート5577をチェック
if lsof -ti:5577 > /dev/null 2>&1; then
    echo "   ポート5577を使用中のプロセスを停止中..."
    lsof -ti:5577 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}✅ クリーンアップ完了${NC}"

# 1. FastAPI サーバー起動
echo -e "${BLUE}🚀 FastAPI サーバー起動中...${NC}"
nohup uvicorn api.main:app --reload --port 5577 --host 127.0.0.1 \
    > /tmp/back2task/api.log 2>&1 & 
API_PID=$!
echo "$API_PID" > /tmp/back2task/api.pid

# サーバー起動待機
echo "   サーバー起動を待機中..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:5577/status > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ FastAPI サーバー起動完了 (PID: $API_PID)${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

if ! curl -s http://127.0.0.1:5577/status > /dev/null 2>&1; then
    echo -e "${RED}   ❌ FastAPI サーバー起動失敗${NC}"
    cat /tmp/back2task/api.log
    exit 1
fi

# 2. Event Pump 起動
echo -e "${BLUE}👀 Event Pump (監視システム) 起動中...${NC}"
nohup python watchers/pump.py --api-url http://127.0.0.1:5577/events --interval 3.0 \
    > /tmp/back2task/pump.log 2>&1 &
PUMP_PID=$!
echo "$PUMP_PID" > /tmp/back2task/pump.pid

# Event Pump起動確認
sleep 3
if ps -p "$PUMP_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Event Pump 起動完了 (PID: $PUMP_PID)${NC}"
else
    echo -e "${RED}   ❌ Event Pump 起動失敗${NC}"
    cat /tmp/back2task/pump.log
    exit 1
fi

# 3. LLMサーバーチェック（オプション）
echo -e "${BLUE}🤖 LLMサーバーチェック中...${NC}"
if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ LLMサーバー利用可能${NC}"
    LLM_STATUS="利用可能"
else
    echo -e "${YELLOW}   ⚠️  LLMサーバーが見つかりません（ルールベース判定で動作）${NC}"
    LLM_STATUS="なし"
fi

# 起動完了
echo ""
echo -e "${GREEN}🎉 Back2Task 起動完了！${NC}"
echo "================================"
echo -e "${BLUE}📊 サービス状態:${NC}"
echo "   • API サーバー: http://127.0.0.1:5577 (PID: $API_PID)"
echo "   • Event Pump: 監視中 (PID: $PUMP_PID)"
echo "   • LLM サーバー: $LLM_STATUS"
echo ""
echo -e "${BLUE}🎮 使用方法:${NC}"
echo "   • タスク開始: curl -X POST http://127.0.0.1:5577/focus/start -H 'Content-Type: application/json' -d '{\"task_id\":\"work\",\"minutes\":25}'"
echo "   • 状態確認: curl http://127.0.0.1:5577/status"
echo "   • ログ確認: tail -f /tmp/back2task/*.log"
echo "   • 停止: ./stop.sh"
echo ""
echo -e "${BLUE}📁 ログファイル:${NC}"
echo "   • API: /tmp/back2task/api.log"
echo "   • Event Pump: /tmp/back2task/pump.log"
echo ""

# 状態監視ループ（オプション）
if [[ "$1" == "--monitor" ]]; then
    echo -e "${YELLOW}📊 リアルタイム監視モード (Ctrl+C で終了)${NC}"
    echo ""
    
    while true; do
        # API サーバー状態確認
        if curl -s http://127.0.0.1:5577/status > /dev/null 2>&1; then
            API_STATUS="🟢"
        else
            API_STATUS="🔴"
        fi
        
        # Event Pump状態確認
        if ps -p "$PUMP_PID" > /dev/null 2>&1; then
            PUMP_STATUS="🟢"
        else
            PUMP_STATUS="🔴"
        fi
        
        # 現在のタスク状態取得
        TASK_INFO=""
        if STATUS_JSON=$(curl -s http://127.0.0.1:5577/status 2>/dev/null); then
            if echo "$STATUS_JSON" | grep -q '"current_task"'; then
                TASK_ID=$(echo "$STATUS_JSON" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
                ACCUM=$(echo "$STATUS_JSON" | grep -o '"accum":[0-9]*' | cut -d':' -f2)
                GOAL=$(echo "$STATUS_JSON" | grep -o '"goal":[0-9]*' | cut -d':' -f2)
                PRODUCTIVE=$(echo "$STATUS_JSON" | grep -o '"productive":[^,]*' | cut -d':' -f2)
                
                if [[ -n "$TASK_ID" && "$TASK_ID" != "null" ]]; then
                    PROGRESS=$((ACCUM * 100 / GOAL))
                    PROD_ICON=$([ "$PRODUCTIVE" = "true" ] && echo "✅" || echo "⚠️")
                    TASK_INFO="| タスク: $TASK_ID ($PROGRESS%) $PROD_ICON"
                fi
            fi
        fi
        
        printf "\r%s API: %s Event Pump: %s %s" "$(date '+%H:%M:%S')" "$API_STATUS" "$PUMP_STATUS" "$TASK_INFO"
        sleep 2
    done
else
    echo -e "${GREEN}✨ Back2Task が動作中です。停止するには './stop.sh' を実行してください。${NC}"
fi