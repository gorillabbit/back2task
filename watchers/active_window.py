import platform
import psutil
import time
from typing import Dict, Optional

# プラットフォーム固有のインポート
try:
    if platform.system() == "Windows":
        import win32gui
        import win32process

        WINDOWS_AVAILABLE = True
    else:
        WINDOWS_AVAILABLE = False
except ImportError:
    WINDOWS_AVAILABLE = False


def get_active_app() -> Dict[str, Optional[str]]:
    """
    前面ウィンドウのアプリケーション情報を取得する

    Returns:
        Dict containing:
        - active_app: プロセス名 (例: "Code.exe")
        - title: ウィンドウタイトル (例: "main.py - VSCode")
    """
    if WINDOWS_AVAILABLE:
        return _get_active_app_windows()
    else:
        return get_active_app_linux()


def _get_active_app_windows() -> Dict[str, Optional[str]]:
    """Windows環境での前面ウィンドウ取得"""
    try:
        # 前面ウィンドウのハンドルを取得
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"active_app": None, "title": None}

        # ウィンドウタイトルを取得
        title = win32gui.GetWindowText(hwnd)

        # プロセスIDを取得
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        # プロセス情報を取得
        try:
            process = psutil.Process(pid)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"active_app": None, "title": None}

        return {"active_app": process_name, "title": title}

    except Exception:
        return {"active_app": None, "title": None}


def get_active_app_linux() -> Dict[str, Optional[str]]:
    """
    Linux環境での代替実装

    Note: Linux環境では前面ウィンドウの概念が複雑なため、
    最も最近アクティブだったプロセスの推定を行う
    """
    try:
        # X11環境での代替実装
        if _is_x11_available():
            return _get_active_app_x11()

        # Wayland環境または他の環境での代替実装
        return _get_active_app_fallback()

    except Exception:
        return {"active_app": None, "title": None}


def _is_x11_available() -> bool:
    """X11環境が利用可能かチェック"""
    try:
        import subprocess

        result = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_active_app_x11() -> Dict[str, Optional[str]]:
    """X11環境での前面ウィンドウ取得"""
    try:
        import subprocess

        # アクティブウィンドウのIDを取得
        result = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0:
            return {"active_app": None, "title": None}

        # ウィンドウIDを抽出
        window_id = result.stdout.strip().split()[-1]
        if window_id == "0x0":
            return {"active_app": None, "title": None}

        # ウィンドウのプロセスIDを取得
        pid_result = subprocess.run(
            ["xprop", "-id", window_id, "_NET_WM_PID"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        # ウィンドウタイトルを取得
        title_result = subprocess.run(
            ["xprop", "-id", window_id, "_NET_WM_NAME"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        # プロセス名を取得
        process_name = None
        title = None

        if pid_result.returncode == 0:
            try:
                pid_line = pid_result.stdout.strip()
                if "=" in pid_line:
                    pid = int(pid_line.split("=")[-1].strip())
                    process = psutil.Process(pid)
                    process_name = process.name()
            except (ValueError, psutil.NoSuchProcess):
                pass

        # タイトルを解析
        if title_result.returncode == 0:
            title_line = title_result.stdout.strip()
            if "=" in title_line:
                title = title_line.split("=", 1)[-1].strip().strip('"')

        return {"active_app": process_name, "title": title or ""}

    except Exception:
        return {"active_app": None, "title": None}


def _get_active_app_fallback() -> Dict[str, Optional[str]]:
    """
    フォールバック実装：最も多くのCPU使用率またはメモリを使用している
    ユーザープロセスを「アクティブ」とみなす
    """
    try:
        # 現在のユーザーのプロセスのみを対象
        current_user = psutil.Process().username()
        user_processes = []

        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent"]):
            try:
                if proc.info["username"] == current_user:
                    # システムプロセスを除外
                    if not _is_system_process(proc.info["name"]):
                        user_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not user_processes:
            return {"active_app": None, "title": None}

        # CPU使用率でソート（最も活発なプロセス）
        active_process = max(user_processes, key=lambda p: p.cpu_percent() or 0)

        return {
            "active_app": active_process.name(),
            "title": f"Process: {active_process.name()}",  # タイトル代替
        }

    except Exception:
        return {"active_app": None, "title": None}


def _is_system_process(process_name: str) -> bool:
    """システムプロセスかどうかを判定"""
    system_processes = {
        "systemd",
        "kthreadd",
        "ksoftirqd",
        "migration",
        "rcu_",
        "watchdog",
        "dbus",
        "NetworkManager",
        "systemd-",
        "kernel",
        "init",
        "swapper",
    }

    process_lower = process_name.lower()
    return any(sys_proc in process_lower for sys_proc in system_processes)


def monitor_active_window(interval: float = 2.0, callback=None):
    """
    前面ウィンドウを定期的に監視する

    Args:
        interval: 監視間隔（秒）
        callback: 結果を受け取るコールバック関数
    """
    import time

    while True:
        try:
            result = get_active_app()
            if callback:
                callback(result)
            time.sleep(interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"監視エラー: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    # テスト実行
    print("Active Window Watcherを開始...")
    print(f"プラットフォーム: {platform.system()}")
    print(f"Windows API利用可能: {WINDOWS_AVAILABLE}")

    def print_result(result):
        print(f"アクティブアプリ: {result['active_app']}")
        print(f"ウィンドウタイトル: {result['title']}")
        print("-" * 40)

    # 5回監視して終了
    for i in range(5):
        result = get_active_app()
        print_result(result)
        time.sleep(2)
