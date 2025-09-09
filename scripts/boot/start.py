#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

from scripts.boot.utils import (
    API_PID_FILE,
    LOG_DIR,
    PUMP_PID_FILE,
    REPO_ROOT,
    ensure_lms,
    http_ok,
    load_local_env,
    logger,
    run_command,
)

CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008


def background_popen(
    cmd: list[str], stdout_path: Path, stderr_path: Path, env: dict[str, str]
) -> subprocess.Popen[bytes]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (
        stdout_path.open("ab", buffering=0) as stdout_f,
        stderr_path.open("ab", buffering=0) as stderr_f,
    ):
        return subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(REPO_ROOT),
            stdout=stdout_f,
            stderr=stderr_f,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def start_api(env: dict[str, str]) -> None:
    proc = background_popen(
        [
            "uv",
            "run",
            "uvicorn",
            "src.api.main:app",
            "--reload",
            "--port",
            "5577",
            "--host",
            "127.0.0.1",
        ],
        stdout_path=LOG_DIR / "api.log",
        stderr_path=LOG_DIR / "api.err.log",
        env=env,
    )
    API_PID_FILE.write_text(str(proc.pid), encoding="ascii")
    if http_ok("http://127.0.0.1:5577/status", 30):
        logger.info(f"API Server: http://127.0.0.1:5577 が起動 (PID {proc.pid})")
    else:
        logger.warning("FastAPI が応答しません ./log/ 以下を見て")


def start_pump(env: dict[str, str]) -> None:
    proc = background_popen(
        ["uv", "run", "python", "src/watchers/pump.py"],
        stdout_path=LOG_DIR / "pump.log",
        stderr_path=LOG_DIR / "pump.err.log",
        env=env,
    )
    PUMP_PID_FILE.write_text(str(proc.pid), encoding="ascii")
    logger.info(f"Event Pump: が起動 (PID {proc.pid})")


def ensure_lm_studio(llm_url: str, model: str) -> None:
    lms = ensure_lms()

    ps = subprocess.run([lms, "ps"], capture_output=True, text=True, check=False)  # noqa: S603
    if model not in ps.stdout:
        run_command([lms, "load", model])

    if not http_ok(f"{llm_url}/v1/models"):
        run_command([lms, "server", "start"])
        http_ok(f"{llm_url}/v1/models")
    logger.info(f"LLM server: {llm_url} が起動しました")


def main() -> int:
    os.chdir(REPO_ROOT)

    logger.info("================ Back2Task Starting up... ===============")

    load_local_env()
    llm_url = os.environ["LLM_URL"].rstrip("/")
    llm_model = os.environ["LLM_MODEL"]

    child_env = os.environ.copy()

    run_command(["uv", "sync", "--dev"])

    start_api(child_env)
    start_pump(child_env)

    ensure_lm_studio(llm_url, llm_model)

    logger.info("\n============== Back2Task is now running! =================\n")
    logger.info("\nLogs: ./log/api.log, ./log/pump.log")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
