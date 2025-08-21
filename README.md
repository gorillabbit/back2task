# Back2Task

**完全ローカル動作の生産性監視システム with OpenAI gpt-oss-20b**

PC画面・Webカメラ・スマホ画面の状況から「脱線していないか」を判定し、脱線時は即リマインド。指定時間の作業継続でタスク自動完了。

## 特徴

- ✅ **完全ローカル動作**: インターネット接続不要（LLM推論も含む）
- ✅ **OSS LLM使用**: OpenAI gpt-oss-20b (20B parameters)
- ✅ **マルチプラットフォーム**: Windows・Linux・macOS対応
- ✅ **リアルタイム監視**: 2秒間隔での生産性判定
- ✅ **インテリジェントnudging**: LLMベースの適切な注意喚起
- ✅ **プライバシー重視**: 画像・画面データは保存しない

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
- **OS**: Windows 10/11, Ubuntu 20.04+, macOS 11+
- **Python**: 3.11+
- **RAM**: 8GB以上
- **ストレージ**: 2GB以上

### LLM推論用（推奨）
- **GPU**: VRAM 16GB以上（RTX 4090, A4000等）
- **RAM**: 16GB以上
- **Note**: GPU無しでもCPU推論可能（大幅に低速）

## インストール・セットアップ

### 1. プロジェクトクローン
```bash
git clone <repository-url>
cd back2task
```

### 2. Python環境セットアップ
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

#### 3.1 WSL2 (Windows) または Linux環境で vLLM インストール
```bash
# WSL2 Ubuntu または Linux
python3 -m venv ~/venv/vllm
source ~/venv/vllm/bin/activate
pip install vllm>=0.5.0
```

#### 3.2 OpenAI gpt-oss-20b をvLLMで起動
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

### 4. 追加依存関係（オプション）

#### OCR機能（推奨）
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# https://github.com/tesseract-ocr/tesseract からインストーラーをダウンロード

# macOS
brew install tesseract
```

#### 追加Pythonライブラリ（高度な機能用）
```bash
pip install opencv-python ultralytics mediapipe mss pytesseract
```

## 使用方法

### 1. APIサーバー起動
```bash
cd back2task
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn api.main:app --reload --port 5577
```

### 2. Event Pump（監視プロセス）起動
```bash
# 別ターミナルで
cd back2task
source venv/bin/activate
python watchers/pump.py --enable-phone  # スマホ検出有効
```

### 3. フォーカスセッション開始
```bash
# タスク開始（25分セッション）
curl -X POST http://localhost:5577/focus/start \
  -H "Content-Type: application/json" \
  -d '{"task_id":"coding_session","minutes":25}'

# ステータス確認
curl http://localhost:5577/status
```

### 4. タスク設定
`config/tasks.yaml` を編集してタスクを定義：

```yaml
- id: coding_session
  title: プログラミング作業
  minutes: 45
  allow_apps: [Code.exe, python.exe, chrome.exe]
  block_words: [YouTube, TikTok, Twitter, Instagram]

- id: document_writing
  title: ドキュメント作成
  minutes: 30
  allow_apps: [WINWORD.EXE, chrome.exe, notepad.exe]
  block_words: [YouTube, Prime Video, Steam]
```

## API エンドポイント

### セッション管理
- `POST /focus/start` - フォーカスセッション開始
- `GET /status` - 現在のセッション状態取得

### イベント取り込み
- `POST /events` - 監視データの取り込み

### LLM サービス
- `GET /llm/models` - 利用可能モデル一覧
- `POST /llm/nudge` - nudging policy 生成

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

### LLM設定
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

# Watchers
python test_watchers_direct.py

# Notifications
python test_notifications_direct.py
```

### 統合動作確認
```bash
# Event Pump テスト
python watchers/pump.py --test-once

# API + LLM テスト
python test_integration.py
```

## 監視される内容

### 生産的な活動
- IDE・エディタ（VSCode, PyCharm, Vim等）
- ターミナル・コマンドライン
- 技術ドキュメント・Stack Overflow
- GitHub・コードレビュー
- 仕事関連のWebサイト

### 非生産的な活動
- 動画サイト（YouTube, Netflix, TikTok等）
- SNS（Twitter, Instagram, Facebook等）
- ゲーム（Steam, Epic Games等）
- ニュースサイト（業務と無関係）
- スマートフォン使用

## プライバシー・セキュリティ

- 🔒 **完全ローカル**: データは外部に送信されません
- 🔒 **画像非保存**: スクリーンショット・カメラ画像は保存されません
- 🔒 **最小データ**: 必要最小限の情報のみ処理
- 🔒 **暗号化**: 設定ファイルは暗号化可能（オプション）

## トラブルシューティング

### LLM サーバー接続エラー
```bash
# サーバー状態確認
curl http://localhost:8000/v1/models

# ログ確認
tail -f ~/.cache/vllm/logs/*.log
```

### カメラ・OCR エラー
```bash
# 権限確認
ls -la /dev/video*

# Tesseract確認
tesseract --version
```

### 通知が表示されない
```bash
# Linux: 通知デーモン確認
systemctl --user status notification-daemon

# Windows: PowerShell権限確認
Get-ExecutionPolicy
```

## 拡張・カスタマイズ

### 新しいWatcher追加
```python
# watchers/custom_watcher.py
def get_custom_data():
    return {"custom_metric": "value"}

# watchers/pump.py に統合
```

### カスタムLLMプロンプト
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