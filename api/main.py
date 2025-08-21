from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from dataclasses import asdict

# LLMサービスをインポート
from api.services.llm import LLMService, NudgingPolicy, create_llm_service

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="Back2Task AI Assistant",
    description="AI-powered productivity monitoring API",
)

# グローバルな状態管理
STATE: Dict[str, Any] = {
    "focus_target": "一般的な作業",  # ユーザーが集中したいタスク
    "productive": True,  # 現在、生産的かどうか
    "last_nudge": None,  # 最後のNudge情報
    "llm_service": None,  # LLMサービスインスタンス
}

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
    print(f"LLM Service Available: {is_ready}")


# --- APIエンドポイント定義 ---


@app.post("/focus/update")
async def update_focus_target(req: FocusUpdate):
    """ユーザーのフォーカスターゲット（集中したい作業内容）を更新する"""
    STATE["focus_target"] = req.target
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

    return {"ok": True, "productive": is_productive, "policy": STATE["last_nudge"]}


@app.get("/status")
async def get_current_status():
    """現在のシステム状態を取得する"""
    # llm_serviceはJSONシリアライズできないので除外
    status_info = {k: v for k, v in STATE.items() if k != "llm_service"}
    return status_info


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
