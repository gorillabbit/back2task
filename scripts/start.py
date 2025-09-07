#!/usr/bin/env python3
"""Back2Task unified launcher (Windows/macOS/Linux)"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from utils import REPO_ROOT, error, info, ok, warn


def load_env_local(path: Path) -> None:
    env_path = path / ".env.local"
    if not env_path.exists():
        error(f".env.local not found at {env_path}")
        raise SystemExit(1)
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
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
    try:
        with urlopen(url, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except URLError:
        return False
    except Exception:
        return False


def wait_http(url: str, attempts: int = 30, interval: float = 1.0) -> bool:
    for _ in range(attempts):
        if http_ok(url):
            return True
        time.sleep(interval)
        print(".", end="", flush=True)
    print()
    return http_ok(url)


def background_popen(
    cmd: list[str], stdout_path: Path, stderr_path: Path, env: dict[str, str]
) -> subprocess.Popen:
    from utils import LOG_DIR

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_f = open(stdout_path, "ab", buffering=0)
    stderr_f = open(stderr_path, "ab", buffering=0)

    creationflags = 0
    start_new_session = False
    if platform.system() == "Windows":
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
    else:
        start_new_session = True

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=stdout_f,
        stderr=stderr_f,
        env=env,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    return proc


def ensure_uv_and_sync() -> None:
    if shutil.which("uv") is None:
        error("uv not found. Install from https://docs.astral.sh/uv/")
        if platform.system() == "Windows":
            print("e.g. PowerShell:  irm https://astral.sh/uv/install.ps1 | iex")
        else:
            print("e.g. curl -LsSf https://astral.sh/uv/install.sh | sh")
        raise SystemExit(1)
    info("Syncing dependencies with uv (including dev)...")
    subprocess.run(["uv", "sync", "--dev"], check=True)
    ok("Dependencies synced")


def start_api(env: dict[str, str]) -> int:
    from utils import API_PID_FILE, LOG_DIR

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
    print("   Waiting for server to respond...")
    if wait_http("http://127.0.0.1:5577/status", attempts=30):
        ok(f"FastAPI server up (PID {proc.pid})")
    else:
        warn("FastAPI server did not respond in time. Check logs under ./log/")
    return proc.pid


def start_pump(env: dict[str, str]) -> int:
    from utils import LOG_DIR, PUMP_PID_FILE

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
        ps = subprocess.run([lms, "ps"], capture_output=True, text=True, check=False)
        if model.lower() in ps.stdout.lower():
            info(f"Model already loaded: {model}")
        else:
            info(f"Loading model: {model}")
            subprocess.run([lms, "load", model], check=True)
    except Exception as e:
        warn(f"Failed to ensure model load via lms: {e}")

    try:
        subprocess.run([lms, "server", "start"], check=False)
    except Exception as e:
        warn(f"Failed to start LM Studio server: {e}")

    print("   Waiting for LLM server to respond...")
    if wait_http(f"{llm_url}/v1/models", attempts=60):
        ok("LM Studio server is up")
        return True
    warn("Could not reach LLM server after auto-start attempts")
    return False


def main() -> int:
    os.chdir(REPO_ROOT)
    print("===============================")
    print(" Back2Task Starting up...")
    print("===============================")

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

    print()
    print("===============================")
    print(" Back2Task is now running!")
    print("===============================")
    print()
    print(f"  - API Server: http://127.0.0.1:5577  (PID: {api_pid} )")
    print(f"  - Event Pump: running                (PID: {pump_pid} )")
    print(
        "  - LLM Server: {}".format(
            f"Available ({llm_url} )" if llm_ok else "Unreachable (AI disabled)"
        )
    )
    print()
    print("Logs: ./log/api.log, ./log/pump.log")
    print("Stop: python scripts/stop.py or python3 scripts/stop.py")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        error(
            f"Command failed with exit code {e.returncode}: "
            f"{(' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd)}"
        )
        raise SystemExit(e.returncode or 1)
