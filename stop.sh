#!/bin/bash
# Back2Task 停止スクリプト

# 色付きメッセージ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Back2Task 停止中...${NC}"
echo "================================"

# PIDファイルから停止
stopped_count=0

if [[ -f "/tmp/back2task/api.pid" ]]; then
    API_PID=$(cat /tmp/back2task/api.pid)
    if ps -p "$API_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}📡 APIサーバーを停止中 (PID: $API_PID)...${NC}"
        kill "$API_PID" 2>/dev/null || true
        sleep 2
        
        # 強制終了が必要な場合
        if ps -p "$API_PID" > /dev/null 2>&1; then
            echo "   強制終了中..."
            kill -9 "$API_PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}   ✅ APIサーバー停止完了${NC}"
        ((stopped_count++))
    fi
    rm -f /tmp/back2task/api.pid
fi

if [[ -f "/tmp/back2task/pump.pid" ]]; then
    PUMP_PID=$(cat /tmp/back2task/pump.pid)
    if ps -p "$PUMP_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}👀 Event Pumpを停止中 (PID: $PUMP_PID)...${NC}"
        kill "$PUMP_PID" 2>/dev/null || true
        sleep 2
        
        # 強制終了が必要な場合
        if ps -p "$PUMP_PID" > /dev/null 2>&1; then
            echo "   強制終了中..."
            kill -9 "$PUMP_PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}   ✅ Event Pump停止完了${NC}"
        ((stopped_count++))
    fi
    rm -f /tmp/back2task/pump.pid
fi

# ポート5577を使用中のプロセスを停止
if lsof -ti:5577 > /dev/null 2>&1; then
    echo -e "${YELLOW}🔌 ポート5577のプロセスを停止中...${NC}"
    lsof -ti:5577 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}   ✅ ポート解放完了${NC}"
    ((stopped_count++))
fi

# ログファイルの最新状態を表示
if [[ -f "/tmp/back2task/api.log" ]]; then
    echo -e "${BLUE}📋 最新のAPIログ:${NC}"
    tail -3 /tmp/back2task/api.log | sed 's/^/   /'
fi

if [[ -f "/tmp/back2task/pump.log" ]]; then
    echo -e "${BLUE}📋 最新のEvent Pumpログ:${NC}"
    tail -3 /tmp/back2task/pump.log | sed 's/^/   /'
fi

echo ""
if [[ $stopped_count -gt 0 ]]; then
    echo -e "${GREEN}🎉 Back2Task 停止完了！ ($stopped_count プロセス停止)${NC}"
else
    echo -e "${YELLOW}ℹ️  停止すべきプロセスが見つかりませんでした${NC}"
fi

echo ""
echo -e "${BLUE}💡 再起動するには: ./start.sh${NC}"
echo -e "${BLUE}📁 ログファイルは /tmp/back2task/ に保存されています${NC}"