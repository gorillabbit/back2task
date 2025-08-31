"""Idle detection helpers (Windows uses LASTINPUTINFO; others fallback to 0)."""

from __future__ import annotations

import sys
from typing import Any, ClassVar

if sys.platform == "win32":
    # Windows 専用の ctypes 構成要素だけこのブロックで import する
    from ctypes import Structure, byref, sizeof, windll, wintypes

    class LASTINPUTINFO(Structure):
        """Windows LASTINPUTINFO structure."""

        _fields_: ClassVar[Any] = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]

    def get_idle_ms() -> int:
        """最後の入力からの経過時間をミリ秒で取得（Windows）。"""
        lii = LASTINPUTINFO()
        lii.cbSize = sizeof(LASTINPUTINFO)
        try:
            ok = windll.user32.GetLastInputInfo(byref(lii))
        except OSError:
            return 0
        else:
            if ok:
                current_tick = int(windll.kernel32.GetTickCount())
                idle_time = int(current_tick - lii.dwTime)
                return max(0, idle_time)
            return 0

else:
    # 非Windows（CI等）は 0 を返すフォールバック
    def get_idle_ms() -> int:
        """非Windowsでは 0 を返すフォールバック実装。"""
        return 0


def is_idle(threshold_ms: int = 5000) -> bool:
    """指定した閾値を超えてアイドル状態かチェック."""
    return get_idle_ms() >= threshold_ms


if __name__ == "__main__":  # pragma: no cover
    import time

    for _ in range(3):
        _ = get_idle_ms()
        _ = is_idle(5000)  # 5秒閾値
        time.sleep(1)
