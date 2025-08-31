__all__ = ["EventModel"]


from typing import TypedDict


class EventModel(TypedDict):
    """監視イベントのデータモデル."""

    active_app: str | None
    title: str | None
    url: str | None
    idle_ms: int | None
    ocr: str | None
    phone: str | None
    phone_detected: bool | None
    screenshot: str | None  # base64エンコードされたスクリーンショット


class NudgingPolicy(TypedDict):
    """Nudging policy response structure."""

    action: str  # "quiet", "gentle_nudge", "strong_nudge"
    reason: str
    tip: str | None
    confidence: float


class IngestEventModel(TypedDict):
    productive: bool
    policy: NudgingPolicy
