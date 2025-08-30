import ctypes  # 再確認（型定義に使用）
import time


class LASTINPUTINFO(ctypes.Structure):
    """Windows LASTINPUTINFO structure."""

    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_ms() -> int:
    """最後の入力からの経過時間をミリ秒で取得."""
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            current_tick = ctypes.windll.kernel32.GetTickCount()
            idle_time = current_tick - lii.dwTime
            return max(0, idle_time)
        return 0
    except Exception:
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


if __name__ == "__main__":
    # テスト実行

    # 10回監視して終了
    for _i in range(10):
        idle_ms = get_idle_ms()
        idle_state = is_idle(5000)  # 5秒閾値
        time.sleep(2)
