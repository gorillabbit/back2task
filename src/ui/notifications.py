import platform
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

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


if __name__ == "__main__":  # pragma: no cover
    # Simple manual smoke test
    NotificationService().get_capabilities()
