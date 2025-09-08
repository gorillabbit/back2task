#!/usr/bin/env python3
import contextlib
import os
from pathlib import Path

import psutil
from utils import (
    API_PID_FILE,
    PUMP_PID_FILE,
    REPO_ROOT,
    ensure_lms,
    load_local_env,
    logger,
    run_command,
)

API_PORT = 5577


def stop_by_pid_file(path: Path) -> None:
    if not path.exists():
        return
    pid = int(path.read_text(encoding="ascii"))
    try:
        proc = psutil.Process(pid)
        proc.terminate()
    except psutil.NoSuchProcess:
        logger.info("すでに停止済みです")
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def stop_llm_server() -> None:
    load_local_env()
    model = os.environ.get("LLM_MODEL", "")

    lms = ensure_lms()

    run_command([lms, "unload", model])
    run_command([lms, "server", "stop"])
    logger.info("LLM server 停止しました")


def main() -> int:
    os.chdir(REPO_ROOT)

    logger.info("============== Back2Task 停止中 ================")

    # APIとPUMPを停止
    stop_by_pid_file(API_PID_FILE)
    stop_by_pid_file(PUMP_PID_FILE)

    stop_llm_server()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
