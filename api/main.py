from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from dataclasses import asdict
from collections import deque

# LLMサービスをインポート
from api.services.llm import LLMService, NudgingPolicy, create_llm_service

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="Back2Task AI Assistant",
    description="AI-powered productivity monitoring API",
)

# グローバルな状態管理
STATE: Dict[str, Any] = {
    "focus_target": "一般的な作業",
    "productive": True,
    "last_nudge": None,
    "llm_service": None,
    "last_event": None,  # 最新のイベントを保存
    "logs": deque(maxlen=100),  # ログを保存 (最大100件)
}

# --- ロギング ---


def log_message(message: str):
    """コンソールに出力し、ログキューにも追加する"""
    print(message)
    STATE["logs"].append(message)


# --- Pydanticモデル定義 ---


class FocusUpdate(BaseModel):
    """フォーカスターゲット更新リクエストのモデル"""

    target: str

    @field_validator("target")
    @classmethod
    def target_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("target must not be empty")
        return v


class Event(BaseModel):
    """監視イベントのデータモデル"""

    active_app: Optional[str] = None
    title: Optional[str] = ""
    url: Optional[str] = ""
    idle_ms: Optional[int] = 0
    ocr: Optional[str] = ""
    phone: Optional[str] = ""
    phone_detected: Optional[bool] = False
    screenshot: Optional[str] = None  # base64エンコードされたスクリーンショット


# --- アプリケーションのライフサイクルイベント ---


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にLLMサービスを初期化"""
    STATE["llm_service"] = create_llm_service()
    is_ready = STATE["llm_service"].is_available()
    log_message(f"LLM Service Available: {is_ready}")


# --- APIエンドポイント定義 ---


@app.post("/focus/update")
async def update_focus_target(req: FocusUpdate):
    """ユーザーのフォーカスターゲット（集中したい作業内容）を更新する"""
    STATE["focus_target"] = req.target
    log_message(f"Focus target updated to: {req.target}")
    return {"ok": True, "focus_target": req.target}


@app.post("/events")
async def ingest_event(event: Event):
    """監視イベントを取り込み、AIで生産性を判定する"""
    llm_service: LLMService = STATE["llm_service"]
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM Service not available")

    # AIによる生産性評価
    is_productive, policy = _evaluate_productivity_by_ai(
        event, llm_service, STATE["focus_target"]
    )

    # 状態を更新
    STATE["productive"] = is_productive
    STATE["last_nudge"] = asdict(policy) if policy else None
    STATE["last_event"] = event.model_dump()

    log_message(
        f"Event processed. Productive: {is_productive}. Nudge action: {policy.action if policy else 'N/A'}"
    )

    return {"ok": True, "productive": is_productive, "policy": STATE["last_nudge"]}


@app.get("/status")
async def get_current_status():
    """現在のシステム状態を取得する"""
    status_info = {
        k: v for k, v in STATE.items() if k not in ["llm_service", "logs", "last_event"]
    }
    return status_info


# --- モニタリング用エンドポイント ---


@app.get("/api/monitoring_data")
async def get_monitoring_data():
    """モニタリングUIに最新データを提供する"""
    return {
        "last_event": STATE["last_event"],
        "last_nudge": STATE["last_nudge"],
        "logs": list(STATE["logs"]),
        "focus_target": STATE["focus_target"],
        "productive": STATE["productive"],
    }


@app.get("/monitoring", response_class=HTMLResponse)
async def get_monitoring_page():
    """モニタリング用のWebページを返す"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Back2Task Monitor</title>
        <style>
            body { font-family: sans-serif; line-height: 1.6; padding: 20px; background-color: #f4f4f4; color: #333; }
            .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1, h2 { color: #555; }
            .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .grid-item { background: #f9f9f9; padding: 15px; border-radius: 5px; }
            #screenshot { max-width: 100%; max-height: 400px; height: auto; border: 1px solid #ddd; object-fit: contain; }
            pre { background: #eee; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; }
            #logs { height: 300px; overflow-y: scroll; border: 1px solid #ddd; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Back2Task Monitor</h1>
            <div class="grid-container">
                <div class="grid-item">
                    <h2>Last Screenshot</h2>
                    <img id="screenshot" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Last Screenshot">
                </div>
                <div class="grid-item">
                    <h2>AI Response (Nudge Policy)</h2>
                    <pre id="nudge-policy">No data yet.</pre>
                    <h2>Current Status</h2>
                    <pre id="current-status">No data yet.</pre>
                </div>
                <div class="grid-item">
                    <h2>Event Sent to AI</h2>
                    <pre id="event-data">No data yet.</pre>
                </div>
                <div class="grid-item">
                    <h2>Logs</h2>
                    <div id="logs"></div>
                </div>
            </div>
        </div>
        <script>
            async function fetchData() {
                try {
                    const response = await fetch('/api/monitoring_data');
                    const data = await response.json();

                    // Screenshot
                    const screenshotImg = document.getElementById('screenshot');
                    if (data.last_event && data.last_event.screenshot) {
                        screenshotImg.src = `data:image/jpeg;base64,${data.last_event.screenshot}`;
                    }

                    // Nudge Policy
                    document.getElementById('nudge-policy').textContent = JSON.stringify(data.last_nudge, null, 2);

                    // Current Status
                    document.getElementById('current-status').textContent = `Focus Target: ${data.focus_target}\nProductive: ${data.productive}`;

                    // Event Data
                    const eventData = data.last_event ? { ...data.last_event } : {};
                    delete eventData.screenshot; // Don't show the long base64 string here
                    document.getElementById('event-data').textContent = JSON.stringify(eventData, null, 2);

                    // Logs
                    const logsDiv = document.getElementById('logs');
                    logsDiv.innerHTML = data.logs.map(log => `<div>${log}</div>`).join('');
                    logsDiv.scrollTop = logsDiv.scrollHeight; // Auto-scroll to bottom

                } catch (error) {
                    console.error('Error fetching monitoring data:', error);
                }
            }

            setInterval(fetchData, 3000); // Update every 3 seconds
            window.onload = fetchData; // Initial fetch
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# --- 内部ロジック ---


def _evaluate_productivity_by_ai(
    event: Event, llm: LLMService, task: str
) -> tuple[bool, Optional[NudgingPolicy]]:
    """
    LLMを使用してイベントから生産性を判定する。

    Args:
        event: 監視イベントデータ
        llm: LLMサービスインスタンス
        task: 現在のフォーカスターゲット

    Returns:
        (bool, NudgingPolicy): (生産的かどうか, LLMの判断ポリシー)
    """
    observations = event.model_dump()

    # LLMに判断を依頼
    policy = llm.decide_nudging_policy(task=task, observations=observations)

    # "quiet"アクションは生産的とみなす
    is_productive = policy.action == "quiet"

    return is_productive, policy
