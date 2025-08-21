from fastapi import FastAPI
from pydantic import BaseModel, field_validator
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリケーション起動時にティッカーを開始
    ticker_task = asyncio.create_task(ticker())
    yield
    # シャットダウン時にティッカーを停止
    ticker_task.cancel()

app = FastAPI(
    title="Back2Task API", 
    description="Local task focus monitoring API",
    lifespan=lifespan
)

STATE = {
    "current_task": None,
    "productive": False,
    "done": None,
    "config": {"tick_sec": 2, "slip_tolerance": 5},
}


class FocusStart(BaseModel):
    task_id: str
    minutes: int

    @field_validator('task_id')
    @classmethod
    def task_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('task_id must not be empty')
        return v

    @field_validator('minutes')
    @classmethod
    def minutes_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('minutes must be positive')
        return v


class Event(BaseModel):
    active_app: Optional[str] = None
    title: Optional[str] = ""
    url: Optional[str] = ""
    idle_ms: Optional[int] = 0
    ocr: Optional[str] = ""
    phone: Optional[str] = ""
    phone_detected: Optional[bool] = False


@app.post("/focus/start")
async def start_focus(req: FocusStart):
    """フォーカスセッションを開始する"""
    STATE["current_task"] = {
        "id": req.task_id,
        "goal": req.minutes * 60,  # 分を秒に変換
        "accum": 0,
        "last_obs": {},
        "started_at": time.time(),
    }
    STATE["done"] = None
    return {"ok": True}


@app.post("/events")
async def ingest(event: Event):
    """イベントを取り込み、生産性を判定する"""
    
    # 基本的なルールベース判定
    productive = _evaluate_productivity(event)
    
    STATE["productive"] = productive
    
    # 現在のタスクがある場合は観測データを保存
    task = STATE.get("current_task")
    if task:
        task["last_obs"] = event.model_dump()
    
    return {"ok": True, "productive": productive}


@app.get("/status")
async def status():
    """現在のセッション状態を取得する"""
    return STATE


def _evaluate_productivity(event: Event) -> bool:
    """イベントから生産性を判定する"""
    
    # アイドル時間チェック（5秒以上で非生産的）
    if event.idle_ms and event.idle_ms > 5000:
        return False
    
    # スマホ検出チェック
    if event.phone_detected or (event.phone and event.phone.strip()):
        return False
    
    # ブラックリストアプリ・キーワードチェック
    blacklist_keywords = [
        "youtube", "tiktok", "prime video", "steam", 
        "twitter", "instagram", "facebook", "reddit",
        "おすすめ動画", "trending"
    ]
    
    content_to_check = " ".join([
        event.title or "",
        event.url or "",
        event.ocr or ""
    ]).lower()
    
    for keyword in blacklist_keywords:
        if keyword in content_to_check:
            return False
    
    # その他は生産的とみなす
    return True


async def ticker():
    """定期的にセッション状態を更新する"""
    while True:
        await asyncio.sleep(STATE["config"]["tick_sec"])
        
        task = STATE.get("current_task")
        if not task:
            continue
            
        # 生産的な時間のみ積算
        if STATE["productive"]:
            task["accum"] += STATE["config"]["tick_sec"]
        
        # 目標時間達成で自動完了
        if task["accum"] >= task["goal"]:
            STATE["done"] = task["id"]
            STATE["current_task"] = None


