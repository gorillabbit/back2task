import platform
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui.notifications import (
    NotificationLevel,
    NotificationService,
    get_notification_service,
)


def test_get_notification_service_singleton() -> None:
    first = get_notification_service()
    second = get_notification_service()
    assert first is second


def test_notify_non_windows() -> None:
    service = NotificationService()
    if platform.system() != "Windows":
        assert service.notify("title", "message", NotificationLevel.INFO) is False
