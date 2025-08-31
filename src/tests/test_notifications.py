import platform
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ui.notifications import NotificationLevel, NotificationService


def test_notify_non_windows() -> None:
    """On non-Windows, notify returns False (UI unavailable)."""
    service = NotificationService()
    if platform.system() != "Windows" and (
        service.notify("title", "message", NotificationLevel.INFO) is not False
    ):
        msg = "notify() should return False on non-Windows platforms"
        raise AssertionError(msg)
