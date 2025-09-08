import logging
import shutil
import subprocess
from pathlib import Path
from typing import cast

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "log"
API_PID_FILE = REPO_ROOT / "api_server.pid"
PUMP_PID_FILE = REPO_ROOT / "event_pump.pid"

HTTP_OK_MIN = 200
HTTP_OK_MAX = 400

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("back2task")


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


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=False)  # noqa: S603


def ensure_lms() -> str:
    lms = shutil.which("lms")
    if lms is None:
        error = "lms コマンドが見つかりません"
        raise RuntimeError(error)
    return lms


def load_local_env() -> None:
    load_dotenv(dotenv_path=REPO_ROOT / ".env.local", override=True)
