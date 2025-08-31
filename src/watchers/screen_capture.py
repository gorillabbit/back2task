import base64
import logging
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Any

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
             Noneの場合は画面全体.

        """
        self.bbox = bbox or self._get_primary_monitor_bbox()
        self.last_capture_time: float = 0.0
        logger.info("ScreenCapture initialized | bbox=%s", self.bbox)

    def _get_primary_monitor_bbox(self) -> dict[str, int]:
        """プライマリモニターの実際の解像度を取得."""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                chosen = monitors[1] if len(monitors) > 1 else monitors[0]
                logger.info(
                    "Monitors detected: %s | chosen=%s", len(monitors) - 1, chosen
                )
                return chosen
        except Exception:
            logger.exception("Failed to get primary monitor bbox")
            return {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def capture_screen(self) -> Image.Image | None:
        """指定領域のスクリーンキャプチャを取得.

        Returns:
            PIL.Image: キャプチャされた画像、失敗時はNone

        """
        try:
            with mss.mss() as sct:
                # スクリーンキャプチャを実行
                screenshot = sct.grab(self.bbox)

                # PIL Imageに変換
                return Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )

        except Exception:
            logger.exception("Screen capture failed | bbox=%s", self.bbox)
            return None

    def capture_as_base64(self) -> tuple[str | None, str | None]:
        """スクリーンキャプチャをbase64で返し、失敗時にエラー詳細も返す.

        Returns:
            (base64, error): 成功時は(base64, None)。失敗時は(None, エラーメッセージ)

        """
        try:
            # ここでは例外を握りつぶさずに詳細を返す
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
        except (OSError, ValueError, mss.ScreenShotError) as e:
            # 追加情報としてモニター情報を可能なら付ける
            try:
                with mss.mss() as sct:
                    monitor_count = len(sct.monitors) - 1
            except (OSError, mss.ScreenShotError):
                monitor_count = -1

            err = f"{type(e).__name__}: {e!s} | monitors={monitor_count}"
            err += f"| bbox={self.bbox}"
            return None, err
        else:
            return img_str, None

    def save_screenshot(self) -> str:
        """スクリーンショットを保存.

        Args:
            filename: ファイル名（Noneの場合は自動生成）
            format: 画像形式

        Returns:
            str: 保存されたファイルパス

        """
        filename = f"screenshot_{int(time.time())}.png"

        try:
            image = self.capture_screen()
            if image is None:
                return ""

            # 一時ディレクトリに保存
            temp_dir = Path(tempfile.gettempdir())
            filepath = temp_dir / filename

            image.save(str(filepath), format="PNG")
        except Exception:
            logger.exception("save_screenshot failed")
            return ""
        else:
            return str(filepath)

    def get_screen_info(self) -> dict[str, Any]:
        """スクリーン情報を取得.

        Returns:
            Dict: スクリーン情報

        """
        try:
            with mss.mss() as sct:
                monitors = sct.monitors

                return {
                    "available": True,
                    "monitor_count": len(monitors) - 1,  # monitors[0]は全画面
                    "primary_monitor": monitors[1] if len(monitors) > 1 else None,
                    "all_monitors": monitors[1:] if len(monitors) > 1 else [],
                    "capture_bbox": self.bbox,
                }

        except Exception as e:
            logger.exception("get_screen_info failed")
            return {"available": False, "error": str(e)}
