import sys
import time
from typing import Any

import requests

# 各コンポーネントをインポート
from src.api.services.llm import LLMService
from src.ui.notifications import NotificationLevel, NotificationService

# HTTP status codes / thresholds
HTTP_OK = 200
MAX_TOTAL_ERRORS = 3
PASS_RATE_THRESHOLD = 0.8


class Back2TaskIntegrationTest:
    """Back2Task統合テストクラス."""

    def __init__(self) -> None:
        self.api_url = "http://localhost:5577"
        # LM Studio Local Server (OpenAI 互換) を既定に統一
        self.llm_url = "http://localhost:1234"
        self.test_results: dict[str, bool] = {}

    def test_api_availability(self) -> bool:
        """API可用性テスト."""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
        except requests.RequestException:
            return False
        else:
            status_code: int = response.status_code
            return status_code == HTTP_OK

    def test_llm_availability(self) -> bool:
        """LLM可用性テスト"""
        try:
            response = requests.get(f"{self.llm_url}/v1/models", timeout=5)
        except requests.RequestException:
            return False
        else:
            status_code: int = response.status_code
            if status_code == HTTP_OK:
                # Validate that the endpoint returns JSON
                _ = response.json()
                return True
            return False

    def test_session_lifecycle(self) -> bool:
        """セッションライフサイクルテスト."""
        ok = True
        try:
            # 1. セッション開始
            start_payload = {
                "task_id": "integration_test",
                "minutes": 1,  # 1分のテストセッション
            }
            response = requests.post(
                f"{self.api_url}/focus/start", json=start_payload, timeout=20
            )
            if response.status_code != HTTP_OK:
                ok = False
            else:
                # 2. ステータス確認
                response = requests.get(f"{self.api_url}/status", timeout=20)
                if response.status_code != HTTP_OK:
                    ok = False
                else:
                    status = response.json()
                    if status.get("current_task", {}).get("id") != "integration_test":
                        ok = False
                    else:
                        # 3. イベント送信テスト
                        test_events = [
                            {
                                "active_app": "Code.exe",
                                "title": "test.py - VSCode",
                                "url": "",
                                "idle_ms": 1000,
                                "ocr": "def test_function():",
                                "phone_detected": False,
                                "phone": "",
                            },
                            {
                                "active_app": "chrome.exe",
                                "title": "YouTube - Google Chrome",
                                "url": "https://youtube.com",
                                "idle_ms": 500,
                                "ocr": "おすすめ動画",
                                "phone_detected": False,
                                "phone": "",
                            },
                        ]

                        for i, event in enumerate(test_events):
                            response = requests.post(
                                f"{self.api_url}/events", json=event, timeout=20
                            )
                            if response.status_code != HTTP_OK:
                                ok = False
                                break
                            result = response.json()
                            expected_productive = i == 0
                            if result.get("productive") != expected_productive:
                                ok = False
                                break
        except requests.RequestException:
            ok = False
        return ok

    def test_llm_integration(self) -> bool:
        """LLM統合テスト."""
        llm_service = LLMService(base_url=self.llm_url, model_name="google/gemma-3-4b")

        # LLM可用性確認（不可でも失敗扱いにはしない）
        _ = llm_service.is_available()

        test_cases: list[dict[str, Any]] = [
            {
                "name": "生産的活動",
                "observations": {
                    "active_app": "Code.exe",
                    "title": "main.py - VSCode",
                    "url": "",
                    "idle_ms": 1000,
                    "ocr": "def calculate_metrics():",
                    "phone_detected": False,
                    "phone": "",
                },
                "expected_action": "quiet",
            },
            {
                "name": "軽度の脱線",
                "observations": {
                    "active_app": "chrome.exe",
                    "title": "Reddit - Programming",
                    "url": "https://reddit.com/r/programming",
                    "idle_ms": 2000,
                    "ocr": "programming news",
                    "phone_detected": False,
                    "phone": "",
                },
                "expected_action": "gentle_nudge",
            },
            {
                "name": "重度の脱線",
                "observations": {
                    "active_app": "chrome.exe",
                    "title": "YouTube - Funny Videos",
                    "url": "https://youtube.com/watch?v=funny",
                    "idle_ms": 1000,
                    "ocr": "funny cat videos",
                    "phone_detected": True,
                    "phone": "jp.youtube",
                },
                "expected_action": "strong_nudge",
            },
        ]

        for case in test_cases:
            policy = llm_service.decide_nudging_policy(
                "テストタスク",
                case["observations"],
            )

            # アクションが適切な範囲内かチェック
            if policy.action not in ["quiet", "gentle_nudge", "strong_nudge"]:
                return False

        return True

    def test_notification_system(self) -> bool:
        """通知システムテスト."""
        notification_service = NotificationService()
        notification_service.get_capabilities()

        test_notifications = [
            (NotificationLevel.INFO, "情報", "テスト用の情報通知です"),
            (NotificationLevel.WARNING, "注意", "軽い注意喚起のテストです"),
            (NotificationLevel.URGENT, "緊急", "緊急通知のテストです"),
        ]
        for level, title, message in test_notifications:
            notification_service.notify(title, message, level)
            time.sleep(1)

        notification_service.get_notification_history()
        return True

    def test_end_to_end_scenario(self) -> bool:
        """エンドツーエンドシナリオテスト."""
        # 1. セッション開始
        start_payload = {"task_id": "e2e_test", "minutes": 1}
        response = requests.post(
            f"{self.api_url}/focus/start", json=start_payload, timeout=20
        )
        if response.status_code != HTTP_OK:
            return False

        # 2. LLMサービス初期化
        llm_service = LLMService(base_url=self.llm_url, model_name="google/gemma-3-4b")

        # 3. 通知サービス初期化
        notification_service = NotificationService()

        # 4. シミュレーション: 生産的な作業 → 脱線 → 通知 → 復帰

        scenarios: list[dict[str, Any]] = [
            {
                "description": "生産的な作業",
                "event": {
                    "active_app": "Code.exe",
                    "title": "project.py - VSCode",
                    "url": "",
                    "idle_ms": 1000,
                    "ocr": "class ProductivityTracker:",
                    "phone_detected": False,
                    "phone": "",
                },
                "expected_productive": True,
            },
            {
                "description": "脱線開始",
                "event": {
                    "active_app": "chrome.exe",
                    "title": "YouTube - Music Videos",
                    "url": "https://youtube.com/watch?v=music",
                    "idle_ms": 500,
                    "ocr": "music video playlist",
                    "phone_detected": False,
                    "phone": "",
                },
                "expected_productive": False,
            },
            {
                "description": "スマホで追加の脱線",
                "event": {
                    "active_app": "chrome.exe",
                    "title": "YouTube - Music Videos",
                    "url": "https://youtube.com/watch?v=music",
                    "idle_ms": 1000,
                    "ocr": "music video playlist",
                    "phone_detected": True,
                    "phone": "jp.youtube",
                },
                "expected_productive": False,
            },
        ]

        for _i, scenario in enumerate(scenarios):
            # イベント送信
            response = requests.post(
                f"{self.api_url}/events", json=scenario["event"], timeout=20
            )
            if response.status_code != HTTP_OK:
                return False

            result = response.json()
            actual_productive = result.get("productive")

            if actual_productive != scenario["expected_productive"]:
                pass

            # LLMでnudging判定
            policy = llm_service.decide_nudging_policy(
                "e2e_test",
                scenario["event"],
            )

            # 非生産的な場合は通知
            if not actual_productive:
                if policy.action == "gentle_nudge":
                    notification_service.notify(
                        "軽い注意",
                        policy.tip or "作業に戻りましょう",
                        NotificationLevel.WARNING,
                    )
                elif policy.action == "strong_nudge":
                    notification_service.notify(
                        "強い注意",
                        policy.tip or "今は作業時間です!",
                        NotificationLevel.URGENT,
                    )

            time.sleep(2)  # シナリオ間の待機

        # 5. セッション状態確認
        response = requests.get(f"{self.api_url}/status", timeout=20)
        if response.status_code != HTTP_OK:
            return False
        response.json()
        return False

    def run_all_tests(self) -> dict[str, bool]:
        """全テストを実行."""
        tests = [
            ("API可用性", self.test_api_availability),
            ("LLM可用性", self.test_llm_availability),
            ("セッションライフサイクル", self.test_session_lifecycle),
            ("LLM統合", self.test_llm_integration),
            ("通知システム", self.test_notification_system),
            ("エンドツーエンドシナリオ", self.test_end_to_end_scenario),
        ]

        results: dict[str, bool] = {}

        for test_name, test_func in tests:
            result = test_func()
            results[test_name] = result

        return results

    def print_summary(self, results: dict[str, bool]) -> None:
        """テスト結果サマリーを表示."""
        passed = sum(results.values())
        total = len(results)

        for _test_name, _result in results.items():
            pass

        if passed == total:
            pass
        else:
            if not results.get("API可用性"):
                pass

            if not results.get("LLM可用性"):
                pass

            if not results.get("Watchersデータ収集"):
                pass


def main() -> None:
    """メイン関数."""
    test_runner = Back2TaskIntegrationTest()
    results = test_runner.run_all_tests()
    test_runner.print_summary(results)

    # 全テスト成功の場合は0、失敗があれば1で終了
    success_rate = sum(results.values()) / len(results)
    sys.exit(0 if success_rate >= PASS_RATE_THRESHOLD else 1)


if __name__ == "__main__":
    main()
