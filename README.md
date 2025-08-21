# Back2Task

**完全ローカル動作の生産性監視システム with OpenAI gpt-oss-20b**

PC 画面・Web カメラ・スマホ画面の状況から「脱線していないか」を判定し、脱線時は即リマインド。指定時間の作業継続でタスク自動完了。

## 特徴

-   ✅ **完全ローカル動作**: インターネット接続不要（LLM 推論も含む）
-   ✅ **OSS LLM 使用**: OpenAI gpt-oss-20b (20B parameters)
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
│  vLLM API Server (localhost:8000)                         │
│  └── gpt-oss-20b (OpenAI 20B parameters model)           │
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

### 3. LLM サーバーセットアップ

#### 3.1 WSL2 (Windows) または Linux 環境で vLLM インストール

```bash
# WSL2 Ubuntu または Linux
python3 -m venv ~/venv/vllm
source ~/venv/vllm/bin/activate
pip install vllm>=0.5.0
```

#### 3.2 OpenAI gpt-oss-20b を vLLM で起動

```bash
# GPU使用（推奨）
python -m vllm.entrypoints.openai.api_server \
  --model openai/gpt-oss-20b \
  --served-model-name gpt-oss-20b \
  --max-model-len 32768 \
  --port 8000

# CPU使用（低速）
python -m vllm.entrypoints.openai.api_server \
  --model openai/gpt-oss-20b \
  --served-model-name gpt-oss-20b \
  --max-model-len 16384 \
  --port 8000 \
  --enforce-eager
```

#### 追加 Python ライブラリ（高度な機能用）

```bash
pip install opencv-python ultralytics mediapipe mss pytesseract
```

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
python watchers/pump.py --enable-phone  # スマホ検出有効
````

## API エンドポイント

### セッション管理

-   `POST /focus/start` - フォーカスセッション開始
-   `GET /status` - 現在のセッション状態取得

### イベント取り込み

-   `POST /events` - 監視データの取り込み

### LLM サービス

-   `GET /llm/models` - 利用可能モデル一覧
-   `POST /llm/nudge` - nudging policy 生成

## 設定

### 通知設定

```python
from ui.notifications import NotificationConfig

config = NotificationConfig(
    enable_toast=True,      # デスクトップ通知
    enable_sound=True,      # 音通知
    enable_flash=False,     # 画面フラッシュ
    toast_duration=5        # 通知表示時間（秒）
)
```

### LLM 設定

```python
from api.services.llm import LLMService

llm = LLMService(
    base_url="http://localhost:8000",
    model_name="gpt-oss-20b",
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

### LLM サーバー接続エラー

```bash
# サーバー状態確認
curl http://localhost:8000/v1/models

# ログ確認
tail -f ~/.cache/vllm/logs/*.log
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

## 拡張・カスタマイズ

### 新しい Watcher 追加

```python
# watchers/custom_watcher.py
def get_custom_data():
    return {"custom_metric": "value"}

# watchers/pump.py に統合
```

### カスタム LLM プロンプト

```python
# api/services/llm.py
custom_prompt = """
カスタム指示をここに記述
"""
```

### 通知スタイル変更

```python
# ui/notifications.py
def custom_notification_style():
    # カスタム通知ロジック
    pass
```

## ライセンス

MIT License

## 貢献

Pull requests、Issues、機能提案を歓迎します。

---

**Back2Task** - Stay focused, stay productive! 🎯
