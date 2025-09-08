import sys
import time
from typing import Any, cast

import psutil

if sys.platform == "win32":
    import pywintypes  # pyright: ignore[reportMissingImports]
    import win32gui  # pyright: ignore[reportMissingImports]
    import win32process  # pyright: ignore[reportMissingImports]
else:  # pragma: no cover
    pywintypes = cast("Any", None)
    win32gui = cast("Any", None)
    win32process = cast("Any", None)


def get_active_app() -> dict[str, str | None]:
    """Return the foreground application on Windows."""
    if sys.platform != "win32":
        return {"active_app": None, "title": None}

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
    return {"active_app": process_name, "title": title}


if __name__ == "__main__":  # pragma: no cover
    # テスト実行
    for _ in range(3):
        get_active_app()
        time.sleep(1)
