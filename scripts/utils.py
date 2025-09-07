#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

# Minimal, truly shared utilities only.

# Paths used by both start and stop scripts
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "log"
API_PID_FILE = REPO_ROOT / "api_server.pid"
PUMP_PID_FILE = REPO_ROOT / "event_pump.pid"


# Lightweight logging helpers used in both scripts
def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def error(msg: str) -> None:
    print(f"[ERROR] {msg}")
