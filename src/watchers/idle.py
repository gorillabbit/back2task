"""Windows idle detection helpers using LASTINPUTINFO."""

import ctypes  # 再確認(型定義に使用)
import time
from typing import Any, ClassVar


class LASTINPUTINFO(ctypes.Structure):
    """Windows LASTINPUTINFO structure."""

    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def get_idle_ms() -> int:
    """最後の入力からの経過時間をミリ秒で取得."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    try:
        ok = ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return 0
    else:
        if ok:
            current_tick = int(ctypes.windll.kernel32.GetTickCount())  # type: ignore[attr-defined]
            idle_time = int(current_tick - lii.dwTime)
            return max(0, idle_time)
        return 0


def is_idle(threshold_ms: int = 5000) -> bool:
    """指定した閾値を超えてアイドル状態かチェック.

    Args:
        threshold_ms: アイドル判定の閾値（ミリ秒）

    Returns:
        bool: アイドル状態の場合True

    """
    idle_time = get_idle_ms()
    return idle_time >= threshold_ms


if __name__ == "__main__":  # pragma: no cover
    # Simple manual check loop (development convenience)
    for _ in range(3):
        _ = get_idle_ms()
        _ = is_idle(5000)  # 5秒閾値
        time.sleep(1)
