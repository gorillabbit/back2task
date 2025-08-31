import base64
import logging
import tempfile
import time
from io import BytesIO
from pathlib import Path

import mss
from PIL import Image

# --- Logging setup (module-level) ---
_LOG_DIR = Path(tempfile.gettempdir()) / "back2task"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "pump.log"

logger = logging.getLogger("back2task.watchers.screen_capture")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _fh = logging.FileHandler(str(_LOG_FILE), encoding="utf-8")
    _fh.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(_fh)


class ScreenCapture:
    """スクリーンキャプチャを取得するクラス."""

    def __init__(self, bbox: dict[str, int] | None = None) -> None:
        """初期化する

        Args:
        bbox: キャプチャ領域 {"top": int, "left": int, "width": int, "height": int}
             Noneの場合は画面全体

        """
        self.bbox = bbox or self._get_primary_monitor_bbox()
        self.last_capture_time: float = 0.0
        logger.info("ScreenCapture initialized | bbox=%s", self.bbox)

    def _get_primary_monitor_bbox(self) -> dict[str, int]:
        """プライマリモニターの実際の解像度を取得"""
        with mss.mss() as sct:
            monitors = sct.monitors
            chosen = monitors[1] if len(monitors) > 1 else monitors[0]
            logger.info("Monitors detected: %s | chosen=%s", len(monitors) - 1, chosen)
            return chosen

    def capture_as_base64(self) -> str:
        """スクリーンキャプチャをbase64で返す"""
        with mss.mss() as sct:
            bbox = self.bbox
            screenshot = sct.grab(bbox)
            image = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        self.last_capture_time = time.time()

        return img_str
