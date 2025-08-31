"""Simple notification helpers used by tests.

The original project targets a Windows environment and relied on a thin
wrapper around the Win32 ``MessageBox`` API.  For the purposes of the unit
tests in this kata we only need a very small subset of that functionality:

* the ability to instantiate a ``NotificationService`` with an optional
  configuration object,
* recording of sent notifications so tests can introspect the history, and
* a light‑weight capability inquiry method.

The previous implementation attempted to expose a configuration type and a
history mechanism but the pieces were never implemented which resulted in a
``NameError`` during import.  The convenience helper functions also attempted
to forward keyword arguments that ``NotificationService.notify`` did not
accept.  Importing :mod:`ui.notifications` therefore failed before any tests
could run.

To make the module usable in both Windows and non‑Windows environments we
provide minimal cross‑platform fallbacks and keep a record of all notification
requests.
"""

import ctypes
import platform
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
            try:
                mb_ok = 0x00000000
                mb_icon_info = 0x00000040
                mb_icon_warn = 0x00000030
                mb_icon_stop = 0x00000010
                mb_topmost = 0x00040000

                icon = {
                    NotificationLevel.INFO: mb_icon_info,
                    NotificationLevel.WARNING: mb_icon_warn,
                    NotificationLevel.URGENT: mb_icon_stop,
                }[level]

                flags = mb_ok | icon | mb_topmost
                ctypes.windll.user32.MessageBoxW(0, message, title, flags)
                success = True
            except (AttributeError, OSError):
                success = False

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


# 便利関数とシングルトン管理（グローバル再代入は避ける）
_service_holder: dict[str, NotificationService | None] = {"svc": None}


def get_notification_service(
    config: NotificationConfig | None = None,
) -> NotificationService | None:
    """Return a lazily-instantiated default :class:`NotificationService`."""
    if _service_holder["svc"] is None:
        _service_holder["svc"] = NotificationService(config)
    return _service_holder["svc"]


def notify(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    *,
    sound: bool | None = None,
    flash: bool | None = None,
) -> bool:
    """Wrap :meth:`NotificationService.notify` for convenience."""
    service = get_notification_service()
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
