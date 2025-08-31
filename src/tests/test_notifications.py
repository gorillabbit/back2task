import platform
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ui.notifications import (
    NotificationLevel,
    NotificationService,
    get_notification_service,
)


def test_get_notification_service_singleton() -> None:
    """Ensure the default notification service is a singleton."""
    first = get_notification_service()
    second = get_notification_service()
    if first is not second:
        msg = "Expected get_notification_service() to return the same instance"
        raise AssertionError(msg)


def test_notify_non_windows() -> None:
    """On non-Windows, notify returns False (UI unavailable)."""
    service = NotificationService()
    if platform.system() != "Windows" and (
        service.notify("title", "message", NotificationLevel.INFO) is not False
    ):
        msg = "notify() should return False on non-Windows platforms"
        raise AssertionError(msg)
