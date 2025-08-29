import time
from typing import Dict, Optional, Any
import tempfile
import os
import base64
from io import BytesIO
from PIL import Image
import mss


class ScreenCapture:
    """スクリーンキャプチャを取得するクラス"""

    def __init__(self, bbox: Optional[Dict[str, int]] = None):
        """
        Args:
            bbox: キャプチャ領域 {"top": int, "left": int, "width": int, "height": int}
                 Noneの場合は画面全体
        """
        self.bbox = bbox or self._get_primary_monitor_bbox()
        self.last_capture_time = 0

    def _get_primary_monitor_bbox(self) -> Dict[str, int]:
        """プライマリモニターの実際の解像度を取得"""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                return monitor
        except Exception:
            return {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def capture_screen(self) -> Optional[Image.Image]:
        """
        指定領域のスクリーンキャプチャを取得

        Returns:
            PIL.Image: キャプチャされた画像、失敗時はNone
        """
        try:
            with mss.mss() as sct:
                # スクリーンキャプチャを実行
                screenshot = sct.grab(self.bbox)

                # PIL Imageに変換
                img = Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )

                return img

        except Exception as e:
            print(f"スクリーンキャプチャエラー: {e}")
            return None

    def capture_as_base64(
        self, format: str = "PNG", quality: int = 80
    ) -> Optional[str]:
        """
        スクリーンキャプチャをbase64エンコードして取得

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
            if format.upper() == "JPEG":
                image.save(buffer, format="JPEG", quality=quality)
            else:
                image.save(buffer, format="PNG")

            # base64エンコード
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()

            self.last_capture_time = time.time()

            return img_str

        except Exception as e:
            print(f"base64変換エラー: {e}")
            return None

    def save_screenshot(self) -> str:
        """
        スクリーンショットを保存

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

        except Exception as e:
            print(f"画像保存エラー: {e}")
            return ""

    def get_screen_info(self) -> Dict[str, Any]:
        """
        スクリーン情報を取得

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
            print(f"スクリーン情報取得エラー: {e}")
            return {"available": False, "error": str(e)}


if __name__ == "__main__":
    # テスト実行
    print("Screen Captureを開始...")

    # 画面情報取得
    capture = ScreenCapture()
    info = capture.get_screen_info()
    print(f"スクリーン情報: {info}")

    # スクリーンショット保存テスト
    print("\nスクリーンショット保存テスト...")
    filepath = capture.save_screenshot()
    if filepath:
        print(f"保存成功: {filepath}")
    else:
        print("保存失敗")

    # base64変換テスト
    print("\nbase64変換テスト...")
    base64_data = capture.capture_as_base64()
    if base64_data:
        print(f"base64変換成功: {len(base64_data)} 文字")
    else:
        print("base64変換失敗")
