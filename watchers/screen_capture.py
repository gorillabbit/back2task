"""Screen capture utilities built on top of mss and PIL."""

import base64
import os
import tempfile
import time
from io import BytesIO
from typing import Any

import mss
from PIL import Image


class ScreenCapture:
    """スクリーンキャプチャを取得するクラス."""

    def __init__(self, bbox: dict[str, int] | None = None) -> None:
        """初期化する

        Args:
        bbox: キャプチャ領域 {"top": int, "left": int, "width": int, "height": int}
             Noneの場合は画面全体.

        """
        self.bbox = bbox or self._get_primary_monitor_bbox()
        self.last_capture_time = 0

    def _get_primary_monitor_bbox(self) -> dict[str, int]:
        """プライマリモニターの実際の解像度を取得."""
        try:
            with mss.mss() as sct:
                return sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        except Exception:
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
                    "RGB",
                    screenshot.size,
                    screenshot.bgra,
                    "raw",
                    "BGRX",
                )

        except Exception:
            return None

    def capture_as_base64(
        self, format_type: str = "PNG", quality: int = 80
    ) -> str | None:
        """スクリーンキャプチャをbase64エンコードして取得.

        Args:
            format: 画像形式 ("PNG", "JPEG")
            quality: JPEG品質 (1-100)

        Returns:
            str: base64エンコードされた画像データ、失敗時はNone

        """
        try:
            image = self.capture_screen()
            if image is None:
                return None

            # BytesIOバッファに保存
            buffer = BytesIO()
            if format_type.upper() == "JPEG":
                image.save(buffer, format="JPEG", quality=quality)
            else:
                image.save(buffer, format="PNG")

            # base64エンコード
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()

            self.last_capture_time = time.time()

            return img_str

        except Exception:
            return None

    def save_screenshot(self) -> str:
        """スクリーンショットを保存.

        Args:
            filename: ファイル名（Noneの場合は自動生成）
            format: 画像形式

        Returns:
            str: 保存されたファイルパス

        """
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"

        try:
            image = self.capture_screen()
            if image is None:
                return ""

            # 一時ディレクトリに保存
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)

            image.save(filepath, format="PNG")
            return filepath

        except Exception:
            return ""

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
            return {"available": False, "error": str(e)}


def capture_screenshot_base64(
    format_type: str = "PNG", quality: int = 80
) -> str | None:
    """Capture the primary monitor and return base64 image data.

    This is a convenience wrapper used by the event pump.
    """
    return ScreenCapture().capture_as_base64(format_type=format_type, quality=quality)
