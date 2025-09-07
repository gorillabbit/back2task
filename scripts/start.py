#!/usr/bin/env python3
"""Back2Task unified launcher (Windows/macOS/Linux)"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, cast

import requests
from utils import (
    API_PID_FILE,
    LOG_DIR,
    PUMP_PID_FILE,
    REPO_ROOT,
    error,
    info,
    ok,
    warn,
)

if TYPE_CHECKING:
    from pathlib import Path


HTTP_OK_MIN = 200
HTTP_OK_MAX = 400
CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008


def load_env_local(path: Path) -> None:
    env_path = path / ".env.local"
    if not env_path.exists():
        error(f".env.local not found at {env_path}")
        raise SystemExit(1)
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            os.environ[k] = v
    ok("Loaded .env.local")


def require_env(keys: list[str]) -> None:
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        error(f"Missing required env vars: {', '.join(missing)} (in .env.local)")
        raise SystemExit(1)


def http_ok(url: str, timeout: float = 2.5) -> bool:
    if not url.lower().startswith(("http://", "https://")):
        return False
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return False
    else:
        status = cast("int", getattr(resp, "status_code", 0))
        return HTTP_OK_MIN <= status < HTTP_OK_MAX


def wait_http(url: str, attempts: int = 30, interval: float = 1.0) -> bool:
    for _ in range(attempts):
        if http_ok(url):
            return True
        time.sleep(interval)
        sys.stdout.write(".")
        sys.stdout.flush()
    sys.stdout.write("\n")
    return http_ok(url)


def background_popen(
    cmd: list[str], stdout_path: Path, stderr_path: Path, env: dict[str, str]
) -> subprocess.Popen:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("ab", buffering=0) as stdout_f, stderr_path.open(
        "ab", buffering=0
    ) as stderr_f:
        creationflags = 0
        start_new_session = False
        if platform.system() == "Windows":
            creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        else:
            start_new_session = True

        return subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(REPO_ROOT),
            stdout=stdout_f,
            stderr=stderr_f,
            env=env,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )


def ensure_uv_and_sync() -> None:
    uv = shutil.which("uv")
    if uv is None:
        error("uv not found. Install from https://docs.astral.sh/uv/")
        if platform.system() == "Windows":
            sys.stdout.write(
                "e.g. PowerShell:  irm https://astral.sh/uv/install.ps1 | iex\n"
            )
        else:
            sys.stdout.write(
                "e.g. curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            )
        raise SystemExit(1)
    info("Syncing dependencies with uv (including dev)...")
    subprocess.run([uv, "sync", "--dev"], check=True)  # noqa: S603
    ok("Dependencies synced")


def start_api(env: dict[str, str]) -> int:
    info("Starting FastAPI server (uvicorn)...")
    api_out = LOG_DIR / "api.log"
    api_err = LOG_DIR / "api.err.log"
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
        stdout_path=api_out,
        stderr_path=api_err,
        env=env,
    )
    API_PID_FILE.write_text(str(proc.pid), encoding="ascii")
    sys.stdout.write("   Waiting for server to respond...\n")
    if wait_http("http://127.0.0.1:5577/status", attempts=30):
        ok(f"FastAPI server up (PID {proc.pid})")
    else:
        warn("FastAPI server did not respond in time. Check logs under ./log/")
    return proc.pid


def start_pump(env: dict[str, str]) -> int:
    info("Starting Event Pump...")
    pump_out = LOG_DIR / "pump.log"
    pump_err = LOG_DIR / "pump.err.log"
    proc = background_popen(
        ["uv", "run", "python", "src/watchers/pump.py"],
        stdout_path=pump_out,
        stderr_path=pump_err,
        env=env,
    )
    PUMP_PID_FILE.write_text(str(proc.pid), encoding="ascii")
    time.sleep(2)
    ok(f"Event Pump started (PID {proc.pid})")
    return proc.pid


def ensure_lm_studio(llm_url: str, model: str) -> bool:
    info("Checking LLM server availability...")
    if http_ok(f"{llm_url}/v1/models"):
        ok("LLM server available")
        return True

    warn("LLM server not reachable. Attempting to start LM Studio (Gemma)...")
    lms = shutil.which("lms")
    if lms is None:
        warn("'lms' CLI not found. Skipping auto-start of LM Studio.")
        return False

    try:
        ps = subprocess.run([lms, "ps"], capture_output=True, text=True, check=False)  # noqa: S603
        if model.lower() in ps.stdout.lower():
            info(f"Model already loaded: {model}")
        else:
            info(f"Loading model: {model}")
            subprocess.run([lms, "load", model], check=True)  # noqa: S603
    except (subprocess.SubprocessError, OSError) as e:
        warn(f"Failed to ensure model load via lms: {e}")

    try:
        subprocess.run([lms, "server", "start"], check=False)  # noqa: S603
    except (subprocess.SubprocessError, OSError) as e:
        warn(f"Failed to start LM Studio server: {e}")

    sys.stdout.write("   Waiting for LLM server to respond...\n")
    if wait_http(f"{llm_url}/v1/models", attempts=60):
        ok("LM Studio server is up")
        return True
    warn("Could not reach LLM server after auto-start attempts")
    return False


def main() -> int:
    os.chdir(REPO_ROOT)
    sys.stdout.write("===============================\n")
    sys.stdout.write(" Back2Task Starting up...\n")
    sys.stdout.write("===============================\n")

    load_env_local(REPO_ROOT)
    require_env(["LLM_URL", "LLM_MODEL"])

    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(REPO_ROOT)

    ensure_uv_and_sync()

    api_pid = start_api(child_env)
    pump_pid = start_pump(child_env)

    llm_url = os.environ["LLM_URL"].rstrip("/")
    llm_model = os.environ["LLM_MODEL"]
    llm_ok = ensure_lm_studio(llm_url, llm_model)

    sys.stdout.write("\n")
    sys.stdout.write("===============================\n")
    sys.stdout.write(" Back2Task is now running!\n")
    sys.stdout.write("===============================\n")
    sys.stdout.write("\n")
    sys.stdout.write(
        f"  - API Server: http://127.0.0.1:5577  (PID: {api_pid} )\n"
    )
    sys.stdout.write(
        f"  - Event Pump: running                (PID: {pump_pid} )\n"
    )
    sys.stdout.write(
        "  - LLM Server: {}\n".format(
            f"Available ({llm_url} )" if llm_ok else "Unreachable (AI disabled)"
        )
    )
    sys.stdout.write("\n")
    sys.stdout.write("Logs: ./log/api.log, ./log/pump.log\n")
    sys.stdout.write("Stop: python scripts/stop.py or python3 scripts/stop.py\n")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        error(
            f"Command failed with exit code {e.returncode}: "
            f"{(' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd)}"
        )
        raise SystemExit(e.returncode or 1) from e
