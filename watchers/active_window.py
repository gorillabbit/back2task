import platform
import psutil
import time
from typing import Dict, Optional
import win32gui
import win32process


def get_active_app() -> Dict[str, Optional[str]]:
    """Windows環境での前面ウィンドウ取得"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"active_app": None, "title": None}

        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            process = psutil.Process(pid)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"active_app": None, "title": None}

        return {"active_app": process_name, "title": title}

    except Exception:
        return {"active_app": None, "title": None}


if __name__ == "__main__":
    # テスト実行
    print("Active Window Watcherを開始...")
    print(f"プラットフォーム: {platform.system()}")

    for _ in range(5):
        result = get_active_app()
        print(f"アクティブアプリ: {result['active_app']}")
        print(f"ウィンドウタイトル: {result['title']}")
        print("-" * 40)
        time.sleep(2)
