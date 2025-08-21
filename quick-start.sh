#!/bin/bash
# Back2Task 即座に起動してデモを実行

# 色付きメッセージ
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Back2Task クイックスタート${NC}"
echo "================================"

# 1. Back2Task起動
echo "1️⃣ Back2Taskシステム起動中..."
./start.sh

if [[ $? -ne 0 ]]; then
    echo "❌ 起動失敗"
    exit 1
fi

# 2. 少し待機
echo ""
echo "2️⃣ システム安定化待機中..."
sleep 5

# 3. テストタスク開始
echo ""
echo "3️⃣ テストタスクを開始中..."
curl -X POST http://127.0.0.1:5577/focus/start \
  -H "Content-Type: application/json" \
  -d '{"task_id":"quick_start","minutes":5}' \
  -s | grep -q "ok" && echo "✅ 5分間のテストタスク開始" || echo "❌ タスク開始失敗"

# 4. 状態表示
echo ""
echo "4️⃣ システム状態:"
curl -s http://127.0.0.1:5577/status | python3 -m json.tool

echo ""
echo -e "${GREEN}🎉 Back2Task クイックスタート完了！${NC}"
echo ""
echo "💡 使用方法:"
echo "   • 状態確認: curl http://127.0.0.1:5577/status | python3 -m json.tool"
echo "   • 新タスク: curl -X POST http://127.0.0.1:5577/focus/start -H 'Content-Type: application/json' -d '{\"task_id\":\"my_task\",\"minutes\":25}'"
echo "   • 停止: ./stop.sh"
echo "   • ログ確認: tail -f /tmp/back2task/*.log"