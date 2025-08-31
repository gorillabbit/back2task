"""Event pump that aggregates watcher data and posts to the API."""

import argparse
import importlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import Any

from src.watchers.active_window import get_active_app
from src.watchers.idle import get_idle_ms
from src.watchers.screen_capture import ScreenCapture

requests: ModuleType = importlib.import_module("requests")

# HTTP status codes
HTTP_OK = 200


class EventPump:
    """各Watcherからデータを収集してAPIに送信するクラス."""

    def __init__(
        self,
        api_url: str = "http://localhost:5577/events",
        interval: float = 2.0,
    ) -> None:
        """初期化する

        Args:
        api_url: イベント送信先のAPIエンドポイント
        interval: データ収集間隔(秒)

        """
        self.api_url = api_url
        self.interval = interval
        self.running = False

        # 各Watcherの状態
        self.last_window_info: dict[str, str | None] = {}
        self.last_idle_time = 0
        self.last_screenshot = ""
        self.last_screenshot_error = ""
        self.screenshot_enabled = True

        # エラー管理
        self.error_counts = {"window": 0, "idle": 0, "screenshot": 0, "api": 0}
        self.max_errors = 5

        # 統計情報
        self.stats: dict[str, Any] = {
            "events_sent": 0,
            "errors_total": 0,
            "start_time": None,
            "last_event_time": None,
        }

    def collect_window_data(self) -> dict[str, str | None]:
        """前面ウィンドウ情報を収集."""
        window_info = get_active_app()
        self.last_window_info = window_info
        self.error_counts["window"] = 0  # エラーカウントリセット
        return window_info

    def collect_idle_data(self) -> int:
        """アイドル時間情報を収集."""
        idle_time = get_idle_ms()
        self.last_idle_time = idle_time
        self.error_counts["idle"] = 0
        return idle_time

    def collect_screenshot_data(self) -> str:
        """スクリーンショット情報を収集"""
        screenshot_b64, err = ScreenCapture().capture_as_base64()
        self.last_screenshot_error = err or ""
        return screenshot_b64 or ""

    def collect_all_data(self) -> dict[str, Any]:
        """全てのWatcherからデータを収集."""
        # 並行してデータ収集
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 各Watcherのタスクを投入
            window_future = executor.submit(self.collect_window_data)
            idle_future = executor.submit(self.collect_idle_data)
            screenshot_future = executor.submit(self.collect_screenshot_data)

            # 結果を収集
            window_data = window_future.result(timeout=3)
            idle_time = idle_future.result(timeout=1)
            screenshot_data = screenshot_future.result(timeout=5)

        # データを統合
        return {
            "timestamp": time.time(),
            "active_app": window_data.get("active_app") if window_data else None,
            "title": window_data.get("title", "") if window_data else "",
            "url": "",  # 将来的にブラウザURL取得を追加
            "idle_ms": idle_time,
            "screenshot": screenshot_data if screenshot_data else "",
            "screenshot_error": self.last_screenshot_error,
        }

    def send_event(self, event_data: dict[str, Any]) -> bool:
        """イベントデータをAPIに送信.

        Args:
            event_data: 送信するイベントデータ

        Returns:
            bool: 送信成功時True

        """
        try:
            response = requests.post(self.api_url, json=event_data, timeout=5)
        except requests.exceptions.RequestException:
            self.error_counts["api"] += 1
            return False
        else:
            status_code = int(getattr(response, "status_code", 0))
            ok = status_code == HTTP_OK
            if ok:
                self.error_counts["api"] = 0
                self.stats["events_sent"] += 1
                self.stats["last_event_time"] = time.time()
            else:
                self.error_counts["api"] += 1
            return ok

    def check_api_availability(self) -> bool:
        """APIの可用性をチェック."""
        try:
            # ステータスエンドポイントで確認
            status_url = self.api_url.replace("/events", "/status")
            response = requests.get(status_url, timeout=3)
        except requests.exceptions.RequestException:
            return False
        else:
            status_code: int = response.status_code
            return status_code == HTTP_OK

    def run_once(self) -> bool:
        """1回のデータ収集・送信サイクルを実行.

        Returns:
            bool: 成功時True

        """
        # データ収集
        event_data = self.collect_all_data()

        # API送信
        success = self.send_event(event_data)

        if not success:
            self.stats["errors_total"] += 1

        return success

    def run_continuous(
        self, callback: Callable[[bool, dict[str, Any]], None] | None = None
    ) -> None:
        """連続的なデータ収集・送信を実行.

        Args:
            callback: 各サイクル後に呼ばれるコールバック関数

        """
        self.running = True
        self.stats["start_time"] = time.time()

        # API可用性チェック
        if not self.check_api_availability():
            pass

        try:
            while self.running:
                start_time = time.time()

                # 1サイクル実行
                success = self.run_once()

                # コールバック実行
                if callback:
                    callback(success, self.stats)

                # エラーが多すぎる場合は一時停止
                total_errors = sum(self.error_counts.values())
                if total_errors > self.max_errors * 3:
                    time.sleep(30)
                    # エラーカウントをリセット
                    for key in self.error_counts:
                        self.error_counts[key] = max(0, self.error_counts[key] - 2)

                # 次のサイクルまで待機
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """イベントポンプを停止."""
        self.running = False

        # リソースクリーンアップ
        # スクリーンキャプチャ用のクリーンアップは不要

        # 統計情報表示
        if self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            if runtime > 0:
                pass

    def get_status(self) -> dict[str, Any]:
        """現在の状態を取得."""
        return {
            "running": self.running,
            "api_url": self.api_url,
            "interval": self.interval,
            "screenshot_enabled": self.screenshot_enabled,
            "error_counts": self.error_counts.copy(),
            "stats": self.stats.copy(),
        }


def main() -> None:
    """メイン関数."""
    parser = argparse.ArgumentParser(description="Back2Task Event Pump")
    parser.add_argument(
        "--api-url",
        default="http://localhost:5577/events",
        help="APIエンドポイントURL",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="データ収集間隔(秒)",
    )
    parser.add_argument(
        "--disable-screenshot",
        action="store_true",
        help="スクリーンショット取得を無効化",
    )
    parser.add_argument("--test-once", action="store_true", help="1回だけテスト実行")

    args = parser.parse_args()

    # イベントポンプを作成
    pump = EventPump(api_url=args.api_url, interval=args.interval)

    try:
        if args.test_once:
            # テスト実行
            pump.run_once()
        else:
            # 連続実行
            def status_callback(success: bool, stats: dict[str, Any]) -> None:
                # 進捗の節目でフック可能なスペースを確保
                frequent = stats["events_sent"] % 10 == 0 and stats["events_sent"] > 0
                if frequent or not success:
                    pass

            pump.run_continuous(callback=status_callback)

    finally:
        pump.stop()


if __name__ == "__main__":
    main()
