#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Minimal, truly shared utilities only.

# Paths used by both start and stop scripts
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "log"
API_PID_FILE = REPO_ROOT / "api_server.pid"
PUMP_PID_FILE = REPO_ROOT / "event_pump.pid"


# Lightweight logging helpers used in both scripts
def info(msg: str) -> None:
    sys.stdout.write(f"[INFO] {msg}\n")


def ok(msg: str) -> None:
    sys.stdout.write(f"[OK] {msg}\n")


def warn(msg: str) -> None:
    sys.stdout.write(f"[WARN] {msg}\n")


def error(msg: str) -> None:
    sys.stdout.write(f"[ERROR] {msg}\n")
