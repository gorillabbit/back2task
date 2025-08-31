"""Windows active window helpers using win32 APIs."""

import time

import psutil
import pywintypes
import win32gui
import win32process


def get_active_app() -> dict[str, str | None]:
    """Windows環境での前面ウィンドウ取得."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return {"active_app": None, "title": None}

    try:
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except pywintypes.error:
        return {"active_app": None, "title": None}

    try:
        process = psutil.Process(pid)
        process_name = process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"active_app": None, "title": None}
    else:
        return {"active_app": process_name, "title": title}


if __name__ == "__main__":  # pragma: no cover
    # テスト実行
    for _ in range(3):
        get_active_app()
        time.sleep(1)
