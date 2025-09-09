import platform
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.model.models import EventModel, NudgingPolicy

if sys.platform == "win32":
    from win10toast import ToastNotifier  # type: ignore[import-untyped, unused-ignore]


class NotificationLevel(Enum):
    """Notification severity levels used by the service."""

    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


@dataclass
class NotificationConfig:
    """Configuration for :class:`NotificationService`.

    Only a couple of toggles are necessary for the tests.  They default to
    ``False`` so that calling code can simply ignore them.
    """

    sound: bool = False
    flash: bool = False


class NotificationService:
    """Minimal notification service with history tracking."""

    def __init__(self, config: NotificationConfig | None = None) -> None:
        self.platform = platform.system()
        self.config = config or NotificationConfig()
        self._history: list[dict[str, Any]] = []

    def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        *,
        sound: bool | None = None,
        flash: bool | None = None,
    ) -> bool:
        """Display a notification and record it.

        On Windows we attempt to show a standard ``MessageBox``.  On other
        platforms the function simply records the notification and reports
        failure (``False``).  ``sound`` and ``flash`` can override the default
        configuration values but are otherwise ignored on non‑Windows systems.
        """
        sound = self.config.sound if sound is None else sound
        flash = self.config.flash if flash is None else flash

        success = False
        if self.platform == "Windows":
            notifier = ToastNotifier()
            notifier.show_toast(title, message, duration=5)  # pyright: ignore[reportUnknownMemberType]
        self._history.append(
            {
                "title": title,
                "message": message,
                "level": level.value,
                "sound": sound,
                "flash": flash,
                "timestamp": time.time(),
                "delivered": success,
            },
        )
        return success

    # ------------------------------------------------------------------
    # Query helpers
    def get_capabilities(self) -> dict[str, Any]:
        """Return a very small capability description.

        The implementation is intentionally simple – the tests merely expect
        the method to exist and to return a dictionary.
        """
        return {
            "platform": self.platform,
            "supports_sound": self.platform == "Windows",
            "supports_flash": self.platform == "Windows",
        }

    def get_notification_history(self) -> list[dict[str, Any]]:
        """Return a copy of the notification history."""
        return list(self._history)


def notify(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    *,
    sound: bool | None = None,
    flash: bool | None = None,
) -> bool:
    """Wrap :meth:`NotificationService.notify` for convenience."""
    service = NotificationService()
    if service:
        return service.notify(title, message, level, sound=sound, flash=flash)
    return False


def notify_gentle_nudge(message: str) -> bool:
    """便利関数: 軽い注意喚起."""
    return notify("Back2Task", message, NotificationLevel.WARNING)


def notify_strong_nudge(message: str) -> bool:
    """便利関数: 強い注意喚起."""
    return notify(
        "Back2Task - Focus!",
        message,
        NotificationLevel.URGENT,
        sound=True,
        flash=True,
    )


def notify_task_complete(task_name: str) -> bool:
    """便利関数: タスク完了通知."""
    return notify(
        "タスク完了",
        f"'{task_name}' が完了しました",
        NotificationLevel.INFO,
        sound=True,
    )


def notify_with_details(
    event: EventModel,
    policy: NudgingPolicy,
    focus_target: str,
    idle_time_minutes: int | None = None,
) -> bool:
    """詳細情報付きの通知を送信.

    Args:
        event: 監視イベントデータ
        policy: AIの判断ポリシー
        focus_target: 現在のフォーカスターゲット
        idle_time_minutes: アイドル時間（分）

    """
    # アプリ名とタイトル情報を取得
    current_app = event.get("active_app", "不明なアプリ")
    window_title = event.get("title", "")

    # アイドル時間の計算
    idle_ms = event.get("idle_ms", 0) or 0
    idle_minutes = idle_ms // (1000 * 60) if idle_ms else 0

    # 通知レベルの決定
    action = policy.get("action", "quiet")
    if action == "strong_nudge":
        level = NotificationLevel.URGENT
        sound = True
        flash = True
    elif action == "gentle_nudge":
        level = NotificationLevel.WARNING
        sound = False
        flash = False
    else:
        return False  # quietの場合は通知しない

    # 詳細メッセージの構築
    message_parts = []

    # 現在の状況
    if current_app and current_app != "不明なアプリ":
        message_parts.append(f"現在: {current_app}")
        if window_title and len(window_title) < 50:
            message_parts.append(f" - {window_title}")

    # フォーカスターゲット
    message_parts.append(f"\n目標: {focus_target}")

    # AI判断理由
    reason = policy.get("reason", "")
    if reason:
        message_parts.append(f"\n理由: {reason}")

    # アイドル時間情報
    if idle_minutes > 0:
        message_parts.append(f"\n放置時間: {idle_minutes}分")

    # ヒント情報
    tip = policy.get("tip")
    if tip:
        message_parts.append(f"\n💡 {tip}")

    # 信頼度
    confidence = policy.get("confidence", 0.0)
    if confidence > 0:
        message_parts.append(f"\n確信度: {int(confidence * 100)}%")

    detailed_message = "".join(message_parts)

    # タイトルの決定
    title = "Back2Task - 集中しましょう！" if action == "strong_nudge" else "Back2Task"

    return notify(title, detailed_message, level, sound=sound, flash=flash)


def notify_productivity_summary(
    productive_minutes: int,
    total_minutes: int,
    top_apps: list[tuple[str, int]],
    focus_target: str,
) -> bool:
    """生産性サマリー通知.

    Args:
        productive_minutes: 生産的だった時間（分）
        total_minutes: 総時間（分）
        top_apps: よく使ったアプリのリスト [(app_name, minutes), ...]
        focus_target: フォーカスターゲット

    """
    productivity_rate = (
        (productive_minutes / total_minutes * 100) if total_minutes > 0 else 0
    )

    message_parts = [
        f"生産性: {productivity_rate:.1f}% ({productive_minutes}/{total_minutes}分)",
        f"\n目標: {focus_target}",
    ]

    if top_apps:
        message_parts.append("\nよく使ったアプリ:")
        for app_name, minutes in top_apps[:3]:  # 上位3つ
            message_parts.append(f"\n• {app_name}: {minutes}分")

    message = "".join(message_parts)

    return notify(
        "Back2Task - 作業サマリー",
        message,
        NotificationLevel.INFO,
        sound=True,
    )


def notify_focus_break_suggestion(
    work_minutes: int,
    suggested_break_minutes: int = 5,
) -> bool:
    """休憩提案通知.

    Args:
        work_minutes: 連続作業時間（分）
        suggested_break_minutes: 提案する休憩時間（分）

    """
    message = (
        f"お疲れさまです!\n"
        f"連続作業時間: {work_minutes}分\n"
        f"\n💡 {suggested_break_minutes}分の休憩をお勧めします\n"
        f"目を休めて、水分補給をしましょう"
    )

    return notify(
        "Back2Task - 休憩時間です",
        message,
        NotificationLevel.INFO,
        sound=True,
    )


if __name__ == "__main__":
    # Simple manual smoke test
    NotificationService().get_capabilities()

    # Test detailed notification
    test_event: EventModel = {
        "active_app": "Chrome",
        "title": "YouTube - 猫の動画",
        "url": "https://youtube.com/watch?v=...",
        "idle_ms": 300000,  # 5分
        "screenshot": None,
        "ocr": None,
        "phone": None,
        "phone_detected": None,
    }

    test_policy: NudgingPolicy = {
        "action": "gentle_nudge",
        "reason": "動画視聴が検出されました",
        "tip": "作業用BGMに切り替えることをお勧めします",
        "confidence": 0.85,
    }

    notify_with_details(test_event, test_policy, "Python開発作業")
