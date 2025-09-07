#!/usr/bin/env python3
"""Back2Task unified stopper (Windows/macOS/Linux)"""

from __future__ import annotations

import contextlib
import os
import sys
from typing import TYPE_CHECKING

import psutil
from utils import (
    API_PID_FILE,
    LOG_DIR,
    PUMP_PID_FILE,
    REPO_ROOT,
    info,
    ok,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

API_PORT = 5577

# --- local helpers (stop-only) ---


def _terminate_proc(proc: psutil.Process, name: str) -> bool:
    try:
        if not proc.is_running():
            return False
    except (psutil.Error, OSError):
        return False
    try:
        info(f"Stopping {name} (PID {proc.pid})...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            warn(f"{name} PID {proc.pid} did not exit, killing...")
            proc.kill()
            proc.wait(timeout=3)
        ok(f"Stopped {name} (PID {proc.pid})")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    else:
        return True


def stop_by_pidfile(path: Path, name: str) -> bool:
    if not path.exists():
        return False
    try:
        pid_txt = path.read_text(encoding="ascii").strip()
        pid = int(pid_txt)
    except (OSError, ValueError):
        warn(f"Invalid PID in {path}: {path.read_text(errors='ignore')!r}")
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
        return False
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        warn(f"{name} process not found (stale PID file)")
        path.unlink(missing_ok=True)
        return False
    stopped = _terminate_proc(proc, name)
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)
    return stopped


def iter_procs_on_port(port: int) -> Iterable[psutil.Process]:
    seen = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and getattr(conn.laddr, "port", None) == port:
                pid = conn.pid
                if pid and pid not in seen:
                    seen.add(pid)
                    try:
                        yield psutil.Process(pid)
                    except psutil.NoSuchProcess:
                        continue
    except psutil.Error:
        return []


def stop_by_port(port: int) -> int:
    count = 0
    for proc in iter_procs_on_port(port):
        if _terminate_proc(proc, f"process on port {port}"):
            count += 1
    return count


def tail_log(path: Path, lines: int = 5) -> None:
    if not path.exists():
        return
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        sys.stdout.write(f"--- Tail {path.name} ---\n")
        for line in content[-lines:]:
            sys.stdout.write("   " + line + "\n")
    except OSError as exc:
        warn(f"Could not read log {path}: {exc}")


def main() -> int:
    os.chdir(REPO_ROOT)
    sys.stdout.write("============== Back2Task 停止中 ================\n")

    stopped = 0
    stopped += 1 if stop_by_pidfile(API_PID_FILE, "API server") else 0
    stopped += 1 if stop_by_pidfile(PUMP_PID_FILE, "Event Pump") else 0

    info(f"Freeing port {API_PORT} if occupied...")
    stopped += stop_by_port(API_PORT)

    tail_log(LOG_DIR / "api.log")
    tail_log(LOG_DIR / "pump.log")

    if stopped > 0:
        ok(f"\nBack2Task stopped ({stopped} process(es) terminated)")
    else:
        warn("No Back2Task processes found")
    sys.stdout.write("\nTo start again:\n")
    sys.stdout.write("  - Windows:  python scripts\\start.py\n")
    sys.stdout.write("  - macOS/Linux: python3 scripts/start.py\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
