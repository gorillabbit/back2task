import time
import requests
import asyncio
import threading
from typing import Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import json

# 各Watcherをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from watchers.active_window import get_active_app
from watchers.idle import get_idle_ms
from watchers.screen_ocr import read_snippet
from watchers.webcam_phone import WebcamPhoneDetector


class EventPump:
    """各Watcherからデータを収集してAPIに送信するクラス"""
    
    def __init__(self, api_url: str = "http://localhost:5577/events", interval: float = 2.0):
        """
        Args:
            api_url: イベント送信先のAPIエンドポイント
            interval: データ収集間隔（秒）
        """
        self.api_url = api_url
        self.interval = interval
        self.running = False
        
        # 各Watcherの状態
        self.last_window_info = {}
        self.last_idle_time = 0
        self.last_ocr_text = ""
        self.phone_detector = None
        self.phone_detection_enabled = False
        
        # エラー管理
        self.error_counts = {
            "window": 0,
            "idle": 0,
            "ocr": 0,
            "phone": 0,
            "api": 0
        }
        self.max_errors = 5
        
        # 統計情報
        self.stats = {
            "events_sent": 0,
            "errors_total": 0,
            "start_time": None,
            "last_event_time": None
        }
    
    def initialize_phone_detector(self) -> bool:
        """
        スマートフォン検出器を初期化
        
        Returns:
            bool: 初期化成功時True
        """
        try:
            self.phone_detector = WebcamPhoneDetector()
            
            if not self.phone_detector.initialize_camera():
                print("カメラの初期化に失敗しました")
                return False
            
            # YOLOまたはMediaPipeを初期化
            yolo_ok = self.phone_detector.initialize_yolo()
            mediapipe_ok = self.phone_detector.initialize_mediapipe()
            
            if yolo_ok or mediapipe_ok:
                self.phone_detection_enabled = True
                print("スマートフォン検出器を初期化しました")
                return True
            else:
                print("検出モデルの初期化に失敗しました")
                return False
                
        except Exception as e:
            print(f"スマートフォン検出器初期化エラー: {e}")
            return False
    
    def collect_window_data(self) -> Dict[str, any]:
        """前面ウィンドウ情報を収集"""
        try:
            window_info = get_active_app()
            self.last_window_info = window_info
            self.error_counts["window"] = 0  # エラーカウントリセット
            return window_info
            
        except Exception as e:
            self.error_counts["window"] += 1
            print(f"ウィンドウ情報収集エラー: {e}")
            return self.last_window_info or {"active_app": None, "title": None}
    
    def collect_idle_data(self) -> int:
        """アイドル時間情報を収集"""
        try:
            idle_time = get_idle_ms()
            self.last_idle_time = idle_time
            self.error_counts["idle"] = 0
            return idle_time
            
        except Exception as e:
            self.error_counts["idle"] += 1
            print(f"アイドル時間収集エラー: {e}")
            return self.last_idle_time
    
    def collect_ocr_data(self) -> str:
        """OCRテキスト情報を収集"""
        try:
            # 頻繁なOCRは負荷が高いため、エラーが多い場合はスキップ
            if self.error_counts["ocr"] >= self.max_errors:
                return self.last_ocr_text
            
            ocr_text = read_snippet()
            self.last_ocr_text = ocr_text
            self.error_counts["ocr"] = 0
            return ocr_text
            
        except Exception as e:
            self.error_counts["ocr"] += 1
            print(f"OCR収集エラー: {e}")
            return self.last_ocr_text
    
    def collect_phone_data(self) -> Dict[str, any]:
        """スマートフォン検出情報を収集"""
        if not self.phone_detection_enabled or self.phone_detector is None:
            return {"phone_detected": False, "phone": ""}
        
        try:
            if self.error_counts["phone"] >= self.max_errors:
                return {"phone_detected": False, "phone": ""}
            
            result = self.phone_detector.detect_phone()
            self.error_counts["phone"] = 0
            
            return {
                "phone_detected": result.get("phone_detected", False),
                "phone": "detected" if result.get("phone_detected", False) else "",
                "phone_confidence": result.get("confidence", 0.0),
                "phone_method": result.get("method", "none")
            }
            
        except Exception as e:
            self.error_counts["phone"] += 1
            print(f"スマートフォン検出エラー: {e}")
            return {"phone_detected": False, "phone": ""}
    
    def collect_all_data(self) -> Dict[str, any]:
        """全てのWatcherからデータを収集"""
        # 並行してデータ収集
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 各Watcherのタスクを投入
            window_future = executor.submit(self.collect_window_data)
            idle_future = executor.submit(self.collect_idle_data)
            ocr_future = executor.submit(self.collect_ocr_data)
            phone_future = executor.submit(self.collect_phone_data)
            
            # 結果を収集
            window_data = window_future.result(timeout=3)
            idle_time = idle_future.result(timeout=1)
            ocr_text = ocr_future.result(timeout=5)
            phone_data = phone_future.result(timeout=3)
        
        # データを統合
        event_data = {
            "timestamp": time.time(),
            "active_app": window_data.get("active_app") if window_data else None,
            "title": window_data.get("title", "") if window_data else "",
            "url": "",  # 将来的にブラウザURL取得を追加
            "idle_ms": idle_time,
            "ocr": ocr_text[:200] if ocr_text else "",  # 長すぎる場合は切り詰め
        }
        
        # phone_dataが辞書の場合のみマージ
        if isinstance(phone_data, dict):
            event_data.update(phone_data)
        else:
            event_data.update({"phone_detected": False, "phone": ""})
        
        return event_data
    
    def send_event(self, event_data: Dict[str, any]) -> bool:
        """
        イベントデータをAPIに送信
        
        Args:
            event_data: 送信するイベントデータ
            
        Returns:
            bool: 送信成功時True
        """
        try:
            response = requests.post(
                self.api_url,
                json=event_data,
                timeout=5
            )
            
            if response.status_code == 200:
                self.error_counts["api"] = 0
                self.stats["events_sent"] += 1
                self.stats["last_event_time"] = time.time()
                return True
            else:
                print(f"API送信エラー: HTTP {response.status_code}")
                self.error_counts["api"] += 1
                return False
                
        except requests.exceptions.RequestException as e:
            self.error_counts["api"] += 1
            print(f"API送信エラー: {e}")
            return False
        except Exception as e:
            self.error_counts["api"] += 1
            print(f"予期しない送信エラー: {e}")
            return False
    
    def check_api_availability(self) -> bool:
        """APIの可用性をチェック"""
        try:
            # ステータスエンドポイントで確認
            status_url = self.api_url.replace("/events", "/status")
            response = requests.get(status_url, timeout=3)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def run_once(self) -> bool:
        """
        1回のデータ収集・送信サイクルを実行
        
        Returns:
            bool: 成功時True
        """
        try:
            # データ収集
            event_data = self.collect_all_data()
            
            # API送信
            success = self.send_event(event_data)
            
            if success:
                print(f"イベント送信成功: {event_data['active_app']} (アイドル: {event_data['idle_ms']}ms)")
            else:
                self.stats["errors_total"] += 1
            
            return success
            
        except Exception as e:
            print(f"データ収集・送信エラー: {e}")
            self.stats["errors_total"] += 1
            return False
    
    def run_continuous(self, callback: Optional[Callable] = None):
        """
        連続的なデータ収集・送信を実行
        
        Args:
            callback: 各サイクル後に呼ばれるコールバック関数
        """
        self.running = True
        self.stats["start_time"] = time.time()
        
        print(f"イベントポンプを開始 (間隔: {self.interval}秒)")
        print(f"API エンドポイント: {self.api_url}")
        
        # API可用性チェック
        if not self.check_api_availability():
            print("警告: APIが利用できません。送信は失敗する可能性があります。")
        
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
                    print("エラーが多すぎます。30秒間一時停止します...")
                    time.sleep(30)
                    # エラーカウントをリセット
                    for key in self.error_counts:
                        self.error_counts[key] = max(0, self.error_counts[key] - 2)
                
                # 次のサイクルまで待機
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nイベントポンプを停止します...")
            self.stop()
        except Exception as e:
            print(f"予期しないエラー: {e}")
            self.stop()
    
    def stop(self):
        """イベントポンプを停止"""
        self.running = False
        
        # リソースクリーンアップ
        if self.phone_detector:
            self.phone_detector.cleanup()
        
        # 統計情報表示
        if self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            print(f"\n統計情報:")
            print(f"実行時間: {runtime:.1f}秒")
            print(f"送信イベント数: {self.stats['events_sent']}")
            print(f"エラー総数: {self.stats['errors_total']}")
            if runtime > 0:
                print(f"送信レート: {self.stats['events_sent'] / runtime * 60:.1f} イベント/分")
    
    def get_status(self) -> Dict[str, any]:
        """現在の状態を取得"""
        return {
            "running": self.running,
            "api_url": self.api_url,
            "interval": self.interval,
            "phone_detection_enabled": self.phone_detection_enabled,
            "error_counts": self.error_counts.copy(),
            "stats": self.stats.copy()
        }


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Back2Task Event Pump")
    parser.add_argument("--api-url", default="http://localhost:5577/events", 
                       help="APIエンドポイントURL")
    parser.add_argument("--interval", type=float, default=2.0,
                       help="データ収集間隔（秒）")
    parser.add_argument("--enable-phone", action="store_true",
                       help="スマートフォン検出を有効化")
    parser.add_argument("--test-once", action="store_true",
                       help="1回だけテスト実行")
    
    args = parser.parse_args()
    
    # イベントポンプを作成
    pump = EventPump(api_url=args.api_url, interval=args.interval)
    
    # スマートフォン検出を初期化（オプション）
    if args.enable_phone:
        pump.initialize_phone_detector()
    
    try:
        if args.test_once:
            # テスト実行
            print("テスト実行中...")
            success = pump.run_once()
            print(f"結果: {'成功' if success else '失敗'}")
        else:
            # 連続実行
            def status_callback(success, stats):
                if stats["events_sent"] % 10 == 0 and stats["events_sent"] > 0:
                    print(f"送信済みイベント: {stats['events_sent']}, エラー: {stats['errors_total']}")
            
            pump.run_continuous(callback=status_callback)
            
    except Exception as e:
        print(f"実行エラー: {e}")
    finally:
        pump.stop()


if __name__ == "__main__":
    main()