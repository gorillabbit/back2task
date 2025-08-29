import platform
import ctypes
from enum import Enum
from typing import Optional


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class NotificationService:
    """最小限のWindows用通知サービス（MessageBoxベース）"""

    def __init__(self):
        self.platform = platform.system()

    def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
    ) -> bool:
        """Windowsで簡易通知を表示（OKボタン付きのメッセージボックス）。

        非Windows環境では何もせず False を返す。
        """
        if self.platform != "Windows":
            return False

        try:
            MB_OK = 0x00000000
            MB_ICON_INFO = 0x00000040
            MB_ICON_WARN = 0x00000030
            MB_ICON_STOP = 0x00000010
            MB_TOPMOST = 0x00040000

            icon = {
                NotificationLevel.INFO: MB_ICON_INFO,
                NotificationLevel.WARNING: MB_ICON_WARN,
                NotificationLevel.URGENT: MB_ICON_STOP,
            }[level]

            flags = MB_OK | icon | MB_TOPMOST
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            return True
        except Exception:
            return False


# 便利関数とグローバルインスタンス
_default_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """デフォルトの通知サービスを取得"""
    global _default_service
    if _default_service is None:
        _default_service = NotificationService()
    return _default_service


def notify(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    **kwargs,
) -> bool:
    """便利関数：通知送信"""
    service = get_notification_service()
    return service.notify(title, message, level, **kwargs)


def notify_gentle_nudge(message: str) -> bool:
    """便利関数：軽い注意喚起"""
    return notify("Back2Task", message, NotificationLevel.WARNING)


def notify_strong_nudge(message: str) -> bool:
    """便利関数：強い注意喚起"""
    return notify(
        "Back2Task - Focus!", message, NotificationLevel.URGENT, sound=True, flash=True
    )


def notify_task_complete(task_name: str) -> bool:
    """便利関数：タスク完了通知"""
    return notify(
        "タスク完了",
        f"'{task_name}' が完了しました！",
        NotificationLevel.INFO,
        sound=True,
    )


if __name__ == "__main__":
    # テスト実行
    service = NotificationService()
