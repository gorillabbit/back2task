import platform
import time
from typing import Optional

# プラットフォーム固有のインポート
try:
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes
        WINDOWS_AVAILABLE = True
    else:
        WINDOWS_AVAILABLE = False
except ImportError:
    WINDOWS_AVAILABLE = False

# Linux環境でもctypesは必要（構造体定義のため）
try:
    import ctypes
except ImportError:
    ctypes = None


if ctypes:
    class LASTINPUTINFO(ctypes.Structure):
        """Windows LASTINPUTINFO structure"""
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("dwTime", ctypes.c_uint)
        ]
else:
    LASTINPUTINFO = None


def get_idle_ms() -> int:
    """
    最後の入力からの経過時間をミリ秒で取得する
    
    Returns:
        int: アイドル時間（ミリ秒）
    """
    if WINDOWS_AVAILABLE:
        return _get_idle_ms_windows()
    else:
        return _get_idle_ms_linux()


def _get_idle_ms_windows() -> int:
    """Windows環境でのアイドル時間取得"""
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        
        # GetLastInputInfo API を呼び出し
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            # GetTickCount で現在時刻を取得
            current_tick = ctypes.windll.kernel32.GetTickCount()
            idle_time = current_tick - lii.dwTime
            return max(0, idle_time)  # 負の値を防ぐ
        else:
            return 0
    except Exception:
        return 0


def _get_idle_ms_linux() -> int:
    """
    Linux環境でのアイドル時間取得
    
    Note: Linux環境では正確なアイドル時間の取得が困難なため、
    代替手段を使用する
    """
    try:
        # X11環境の場合
        if _is_x11_available():
            return _get_idle_ms_x11()
        
        # その他の環境では概算値を返す
        return _get_idle_ms_fallback()
        
    except Exception:
        return 0


def _is_x11_available() -> bool:
    """X11環境が利用可能かチェック"""
    try:
        import subprocess
        result = subprocess.run(
            ["xset", "q"],
            capture_output=True,
            text=True,
            timeout=1
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_idle_ms_x11() -> int:
    """X11環境でのアイドル時間取得"""
    try:
        import subprocess
        
        # xprintidle コマンドを試す
        try:
            result = subprocess.run(
                ["xprintidle"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        
        # xset でスクリーンセーバー情報を取得
        result = subprocess.run(
            ["xset", "q"],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode != 0:
            return 0
        
        # Screen Saver の行を探す
        for line in result.stdout.split('\n'):
            if 'Screen Saver' in line:
                # 簡易的な解析（完全ではない）
                return 0  # X11では詳細なアイドル時間取得が複雑
        
        return 0
        
    except Exception:
        return 0


def _get_idle_ms_fallback() -> int:
    """
    フォールバック実装
    
    実際のアイドル時間は取得できないため、ダミー値を返す
    """
    # 実際のアプリケーションでは、より高度な代替手段が必要
    # 例：ファイルシステムの変更監視、プロセス監視など
    return 0


def is_idle(threshold_ms: int = 5000) -> bool:
    """
    指定した閾値を超えてアイドル状態かチェック
    
    Args:
        threshold_ms: アイドル判定の閾値（ミリ秒）
        
    Returns:
        bool: アイドル状態の場合True
    """
    idle_time = get_idle_ms()
    return idle_time >= threshold_ms


def get_idle_seconds() -> float:
    """
    アイドル時間を秒で取得
    
    Returns:
        float: アイドル時間（秒）
    """
    return get_idle_ms() / 1000.0


def monitor_idle(callback=None, interval: float = 1.0, threshold_ms: int = 5000):
    """
    アイドル状態を定期的に監視
    
    Args:
        callback: 状態変化時に呼ばれるコールバック関数
        interval: 監視間隔（秒）
        threshold_ms: アイドル判定の閾値（ミリ秒）
    """
    last_idle_state = False
    
    while True:
        try:
            idle_time = get_idle_ms()
            current_idle_state = idle_time >= threshold_ms
            
            # 状態が変化した場合にコールバックを呼ぶ
            if callback and current_idle_state != last_idle_state:
                callback({
                    "idle": current_idle_state,
                    "idle_ms": idle_time,
                    "idle_seconds": idle_time / 1000.0,
                    "threshold_ms": threshold_ms
                })
            
            last_idle_state = current_idle_state
            time.sleep(interval)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"アイドル監視エラー: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    # テスト実行
    print("Idle Watcherを開始...")
    print(f"プラットフォーム: {platform.system()}")
    print(f"Windows API利用可能: {WINDOWS_AVAILABLE}")
    
    def print_idle_status(status):
        print(f"アイドル状態: {status['idle']}")
        print(f"アイドル時間: {status['idle_seconds']:.1f}秒")
        print("-" * 40)
    
    # 10回監視して終了
    for i in range(10):
        idle_ms = get_idle_ms()
        idle_state = is_idle(5000)  # 5秒閾値
        print(f"#{i+1} アイドル時間: {idle_ms}ms, アイドル状態: {idle_state}")
        time.sleep(2)