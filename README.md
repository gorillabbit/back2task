# Back2Task

**完全ローカル動作の生産性監視システム（LM Studio + Gemma 3 4B 対応）**

PC 画面・Web カメラ・スマホ画面の状況から「脱線していないか」を判定し、脱線時は即リマインド。指定時間の作業継続でタスク自動完了。

## 特徴

-   ✅ **完全ローカル動作**: インターネット接続不要（LLM 推論も含む）
-   ✅ **ローカル LLM 使用**: LM Studio 経由（例: google/gemma-3-4b, 画像理解）
-   ✅ **マルチプラットフォーム**: Windows・Linux・macOS 対応
-   ✅ **リアルタイム監視**: 2 秒間隔での生産性判定
-   ✅ **インテリジェント nudging**: LLM ベースの適切な注意喚起
-   ✅ **プライバシー重視**: 画像・画面データは保存しない

## アーキテクチャ

```
┌─────────────────── Desktop Application ───────────────────┐
│  FastAPI (localhost:5577)                                 │
│  ├── Session Engine (タスク管理・自動完了)                │
│  ├── Event Ingestion (/events エンドポイント)             │
│  └── Status API (/status, /focus/start)                   │
│                                                            │
│  Watchers (並列監視)                                       │
│  ├── Active Window (前面アプリ検出)                       │
│  ├── Idle Detection (マウス・KB無操作検出)                │
│  ├── Screen OCR (画面内容分析)                            │
│  ├── Webcam Phone Detection (スマホ使用検出)              │
│  └── Event Pump (データ統合・送信)                        │
│                                                            │
│  Notification System                                       │
│  ├── Toast/Desktop Notifications                          │
│  ├── Sound Alerts                                         │
│  └── Screen Flash (緊急時)                                │
└────────────────────────────────────────────────────────────┘
                              │
                              │ OpenAI互換API
                              ▼
┌─────────────────── LLM Service ───────────────────────────┐
│  LM Studio Local Server (localhost:1234)                  │
│  └── google/gemma-3-4b (Vision)                           │
│      ├── Nudging Policy Generation                        │
│      ├── Task Breakdown Suggestions                       │
│      └── Contextual Productivity Analysis                 │
└────────────────────────────────────────────────────────────┘
```

## 必要な環境

### 最小要件

-   **OS**: Windows 10/11, Ubuntu 20.04+, macOS 11+
-   **Python**: 3.11+
-   **RAM**: 8GB 以上
-   **ストレージ**: 2GB 以上

### LLM 推論用（推奨）

-   **GPU**: VRAM 16GB 以上（RTX 4090, A4000 等）
-   **RAM**: 16GB 以上
-   **Note**: GPU 無しでも CPU 推論可能（大幅に低速）

## インストール・セットアップ

### 1. プロジェクトクローン

```bash
git clone <repository-url>
cd back2task
```

### 2. Python 環境セットアップ

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.x LM Studio を使う（Gemma 3 4B, 画像入力対応）

LM Studio の Local Server は OpenAI 互換 API を提供します。本プロジェクトはそのまま接続できます。

-   LM Studio でモデルをロード（例: `google/gemma-3-4b`）。Local Server を起動（デフォルト: `http://localhost:1234/v1`）。
-   Back2Task 側は環境変数で接続先とモデル名を指定します。

```bash
# Windows (PowerShell)
$env:LLM_URL = "http://localhost:1234"   # 末尾 /v1 は不要
$env:LLM_MODEL = "google/gemma-3-4b"
# 認証が必要なら（LM Studio 設定に合わせる）
$env:LLM_API_KEY = "lm-studio"
./start.bat

# macOS/Linux (bash/zsh)
export LLM_URL="http://localhost:1234"
export LLM_MODEL="google/gemma-3-4b"
export LLM_API_KEY="lm-studio"   # 任意
./start.sh
```

補足:

-   ストリーミングは未使用、画像リサイズは行いません。Event Pump が取得したスクリーンショットを base64 の data URL として直接送信します。
-   ルールベースの判定は廃止しました。LLM が利用できない・エラー時は `action: "quiet"`（reason にエラー種別）を返すだけで、挙動は最小限に抑えます。

## 使用方法

### 🚀 ワンコマンド起動（推奨）

```bash
cd back2task
./start.sh          # Back2Task全体を起動
./stop.sh           # 停止
./quick-start.sh    # 起動 + デモタスク自動開始
```

### 📊 基本操作

```bash
# 集中するタスクを設定
curl -X POST http://localhost:5577/focus/update \
  -H "Content-Type: application/json" \
  -d '{"target":"新しい機能のコーディング"}'

# ステータス確認
curl http://localhost:5577/status | python3 -m json.tool

```

# ログ確認

tail -f /tmp/back2task/\*.log

````

### 🔧 手動起動（開発用）
```bash
# 1. APIサーバー起動
cd back2task
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn api.main:app --reload --port 5577

# 2. Event Pump（監視プロセス）起動（別ターミナル）
cd back2task
source venv/bin/activate
python watchers/pump.py
````

## API エンドポイント

### セッション管理

-   `POST /focus/start` - フォーカスセッション開始
-   `GET /status` - 現在のセッション状態取得

### イベント取り込み

-   `POST /events` - 監視データの取り込み

### LLM サービス（内部利用）

- 内部で LM Studio の OpenAI 互換エンドポイント（`/v1/chat/completions`）に接続します。

## 設定

### 通知（Windows最小）

```python
from ui.notifications import NotificationService, NotificationLevel

notifier = NotificationService()
notifier.notify("Back2Task", "作業を続けましょう", level=NotificationLevel.INFO)
```
備考: Windows のみで動作（メッセージボックス表示）。他OSでは無効です。

### LLM 設定

```python
from api.services.llm import LLMService

llm = LLMService(
    base_url=os.getenv("LLM_URL", "http://localhost:1234"),
    model_name=os.getenv("LLM_MODEL", "google/gemma-3-4b"),
    timeout=20.0
)
```

## テスト

### 全テスト実行

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### 個別コンポーネントテスト

```bash
# FastAPI Session Engine
python -m pytest tests/api/test_session_engine.py -v

# LLM Service
python -m pytest tests/api/test_llm_service.py -v

# 通知システム
python -m pytest tests/ui/test_notifications.py -v

# Watchers
python -m pytest tests/watchers/ -v
```

### 統合テスト

```bash
# Event Pump テスト
python watchers/pump.py --test-once

# システム全体テスト
python test_integration.py
```

## 監視される内容

### 生産的な活動

-   IDE・エディタ（VSCode, PyCharm, Vim 等）
-   ターミナル・コマンドライン
-   技術ドキュメント・Stack Overflow
-   GitHub・コードレビュー
-   仕事関連の Web サイト

### 非生産的な活動（LLM が画面から自動判定）

-   動画サイト（YouTube, Netflix, TikTok 等）
-   SNS（Twitter, Instagram, Facebook 等）
-   ゲーム（Steam, Epic Games 等）
-   ニュースサイト（業務と無関係）
-   スマートフォンアプリの利用

## プライバシー・セキュリティ

-   🔒 **完全ローカル**: データは外部に送信されません
-   🔒 **画像非保存**: スクリーンショット・カメラ画像は保存されません
-   🔒 **最小データ**: 必要最小限の情報のみ処理
-   🔒 **暗号化**: 設定ファイルは暗号化可能（オプション）

## トラブルシューティング

### LLM サーバー接続エラー（LM Studio）

```bash
# サーバー状態確認（LM Studio Local Server）
curl http://localhost:1234/v1/models

# ログ確認: LM Studio アプリの Local Server コンソールを参照
```

### スクリーンキャプチャエラー

```bash
# Windows での権限確認
# PowerShell で管理者権限が必要な場合があります
```

### 通知が表示されない

```bash
# Linux: 通知デーモン確認
systemctl --user status notification-daemon

# Windows: PowerShell権限確認
Get-ExecutionPolicy
```
