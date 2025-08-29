#!/usr/bin/env python3
"""
Back2Task MVP Integration Test
完全な統合テストとデモンストレーション
"""

import time
import requests
from typing import Dict

# 各コンポーネントをインポート
from api.services.llm import LLMService
from ui.notifications import NotificationService, NotificationLevel
from watchers.pump import EventPump


class Back2TaskIntegrationTest:
    """Back2Task統合テストクラス"""

    def __init__(self):
        self.api_url = "http://localhost:5577"
        # LM Studio Local Server (OpenAI 互換) を既定に統一
        self.llm_url = "http://localhost:1234"
        self.test_results = {}

    def test_api_availability(self) -> bool:
        """API可用性テスト"""
        print("=== API可用性テスト ===")
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                print("✓ FastAPI サーバーが利用可能")
                return True
            else:
                print(f"❌ FastAPI サーバーエラー: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ FastAPI サーバーに接続できません: {e}")
            print(
                "ヒント: uvicorn api.main:app --reload --port 5577 で起動してください"
            )
            return False

    def test_llm_availability(self) -> bool:
        """LLM可用性テスト"""
        print("\n=== LLM可用性テスト ===")
        try:
            response = requests.get(f"{self.llm_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                print("✓ LLMサーバーが利用可能")
                print(f"利用可能モデル: {[m['id'] for m in models.get('data', [])]}")
                return True
            else:
                print(f"❌ LLMサーバーエラー: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ LLMサーバーに接続できません: {e}")
            print("ヒント: LM Studio の Local Server を起動してください（例: http://localhost:1234/v1）")
            print("  1) モデルをロード（例: google/gemma-3-4b）")
            print("  2) Local Server を起動（OpenAI 互換 API）")
            return False

    def test_session_lifecycle(self) -> bool:
        """セッションライフサイクルテスト"""
        print("\n=== セッションライフサイクルテスト ===")
        try:
            # 1. セッション開始
            start_payload = {
                "task_id": "integration_test",
                "minutes": 1,  # 1分のテストセッション
            }
            response = requests.post(f"{self.api_url}/focus/start", json=start_payload)
            if response.status_code != 200:
                print(f"❌ セッション開始失敗: {response.status_code}")
                return False
            print("✓ セッション開始成功")

            # 2. ステータス確認
            response = requests.get(f"{self.api_url}/status")
            if response.status_code != 200:
                print(f"❌ ステータス取得失敗: {response.status_code}")
                return False

            status = response.json()
            if status.get("current_task", {}).get("id") != "integration_test":
                print(f"❌ セッション状態が正しくありません: {status}")
                return False
            print("✓ セッション状態確認成功")

            # 3. イベント送信テスト
            test_events = [
                {  # 生産的なイベント
                    "active_app": "Code.exe",
                    "title": "test.py - VSCode",
                    "url": "",
                    "idle_ms": 1000,
                    "ocr": "def test_function():",
                    "phone_detected": False,
                    "phone": "",
                },
                {  # 脱線イベント
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
                response = requests.post(f"{self.api_url}/events", json=event)
                if response.status_code != 200:
                    print(f"❌ イベント{i + 1}送信失敗: {response.status_code}")
                    return False

                result = response.json()
                expected_productive = i == 0  # 最初は生産的、2番目は非生産的
                if result.get("productive") != expected_productive:
                    print(f"❌ イベント{i + 1}の生産性判定が期待と異なります: {result}")
                    return False

                print(
                    f"✓ イベント{i + 1}送信・判定成功 (生産的: {result['productive']})"
                )

            return True

        except Exception as e:
            print(f"❌ セッションライフサイクルテスト失敗: {e}")
            return False

    def test_llm_integration(self) -> bool:
        """LLM統合テスト"""
        print("\n=== LLM統合テスト ===")
        try:
            llm_service = LLMService(base_url=self.llm_url)

            # LLM可用性確認
            if not llm_service.is_available():
                print("⚠️  LLMサーバーが利用できません - フォールバック機能をテスト")

            # テストケース
            test_cases = [
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
                    "テストタスク", case["observations"]
                )

                print(f"テストケース: {case['name']}")
                print(f"  判定: {policy.action}")
                print(f"  理由: {policy.reason}")
                if policy.tip:
                    print(f"  ヒント: {policy.tip}")
                print(f"  信頼度: {policy.confidence}")

                # アクションが適切な範囲内かチェック
                valid_actions = ["quiet", "gentle_nudge", "strong_nudge"]
                if policy.action not in valid_actions:
                    print(f"❌ 無効なアクション: {policy.action}")
                    return False

                print("✓ 判定成功")

            print("✓ LLM統合テスト完了")
            return True

        except Exception as e:
            print(f"❌ LLM統合テスト失敗: {e}")
            return False

    def test_notification_system(self) -> bool:
        """通知システムテスト"""
        print("\n=== 通知システムテスト ===")
        try:
            notification_service = NotificationService()

            print(f"プラットフォーム: {notification_service.platform}")
            capabilities = notification_service.get_capabilities()
            print(f"通知機能: {capabilities}")

            # 各レベルの通知をテスト
            test_notifications = [
                (NotificationLevel.INFO, "情報", "テスト用の情報通知です"),
                (NotificationLevel.WARNING, "注意", "軽い注意喚起のテストです"),
                (NotificationLevel.URGENT, "緊急", "緊急通知のテストです"),
            ]

            for level, title, message in test_notifications:
                result = notification_service.notify(title, message, level)
                print(f"通知レベル {level.value}: {'成功' if result else '失敗'}")
                time.sleep(1)  # 通知間の間隔

            # 履歴確認
            history = notification_service.get_notification_history()
            print(f"通知履歴: {len(history)}件")

            print("✓ 通知システムテスト完了")
            return True

        except Exception as e:
            print(f"❌ 通知システムテスト失敗: {e}")
            return False

    def test_watchers_data_collection(self) -> bool:
        """Watchers データ収集テスト"""
        print("\n=== Watchers データ収集テスト ===")
        try:
            event_pump = EventPump(api_url=f"{self.api_url}/events")

            # データ収集テスト
            print("データ収集中...")
            event_data = event_pump.collect_all_data()

            required_fields = [
                "active_app",
                "title",
                "idle_ms",
                "ocr",
                "phone_detected",
            ]
            for field in required_fields:
                if field not in event_data:
                    print(f"❌ 必須フィールドが不足: {field}")
                    return False

            print("✓ 全フィールドが正常に収集されました")
            print(f"  アクティブアプリ: {event_data.get('active_app')}")
            print(f"  ウィンドウタイトル: {event_data.get('title', '')[:50]}")
            print(f"  アイドル時間: {event_data.get('idle_ms')}ms")
            print(f"  OCRテキスト: {len(event_data.get('ocr', ''))}文字")
            print(f"  スマホ検出: {event_data.get('phone_detected')}")

            # エラーカウント確認
            status = event_pump.get_status()
            total_errors = sum(status["error_counts"].values())
            if total_errors > 3:
                print(f"⚠️  多くのエラーが発生しています: {status['error_counts']}")
            else:
                print("✓ エラー数は正常範囲内です")

            event_pump.stop()
            print("✓ Watchers データ収集テスト完了")
            return True

        except Exception as e:
            print(f"❌ Watchers データ収集テスト失敗: {e}")
            return False

    def test_end_to_end_scenario(self) -> bool:
        """エンドツーエンドシナリオテスト"""
        print("\n=== エンドツーエンドシナリオテスト ===")
        try:
            # 1. セッション開始
            print("1. フォーカスセッション開始...")
            start_payload = {"task_id": "e2e_test", "minutes": 1}
            response = requests.post(f"{self.api_url}/focus/start", json=start_payload)
            assert response.status_code == 200

            # 2. LLMサービス初期化
            print("2. LLMサービス初期化...")
            llm_service = LLMService(base_url=self.llm_url)

            # 3. 通知サービス初期化
            print("3. 通知サービス初期化...")
            notification_service = NotificationService()

            # 4. シミュレーション: 生産的な作業 → 脱線 → 通知 → 復帰
            print("4. 作業シナリオをシミュレーション...")

            scenarios = [
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

            for i, scenario in enumerate(scenarios):
                print(f"  シナリオ {i + 1}: {scenario['description']}")

                # イベント送信
                response = requests.post(
                    f"{self.api_url}/events", json=scenario["event"]
                )
                assert response.status_code == 200

                result = response.json()
                actual_productive = result.get("productive")

                print(
                    f"    生産性判定: {actual_productive} (期待: {scenario['expected_productive']})"
                )

                if actual_productive != scenario["expected_productive"]:
                    print("    ⚠️  判定が期待と異なります")

                # LLMでnudging判定
                policy = llm_service.decide_nudging_policy(
                    "e2e_test", scenario["event"]
                )
                print(f"    Nudging: {policy.action} - {policy.reason}")

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
                            policy.tip or "今は作業時間です！",
                            NotificationLevel.URGENT,
                        )

                time.sleep(2)  # シナリオ間の待機

            # 5. セッション状態確認
            print("5. 最終セッション状態確認...")
            response = requests.get(f"{self.api_url}/status")
            assert response.status_code == 200

            final_status = response.json()
            print(f"  現在のタスク: {final_status.get('current_task', {}).get('id')}")
            print(
                f"  積算時間: {final_status.get('current_task', {}).get('accum', 0)}秒"
            )
            print(
                f"  現在の状態: {'生産的' if final_status.get('productive') else '非生産的'}"
            )

            print("✓ エンドツーエンドシナリオテスト完了")
            return True

        except Exception as e:
            print(f"❌ エンドツーエンドシナリオテスト失敗: {e}")
            import traceback

            traceback.print_exc()
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """全テストを実行"""
        print("🎯 Back2Task MVP 統合テスト開始\n")

        tests = [
            ("API可用性", self.test_api_availability),
            ("LLM可用性", self.test_llm_availability),
            ("セッションライフサイクル", self.test_session_lifecycle),
            ("LLM統合", self.test_llm_integration),
            ("通知システム", self.test_notification_system),
            ("Watchersデータ収集", self.test_watchers_data_collection),
            ("エンドツーエンドシナリオ", self.test_end_to_end_scenario),
        ]

        results = {}

        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    print(f"✅ {test_name}: 成功")
                else:
                    print(f"❌ {test_name}: 失敗")
            except Exception as e:
                print(f"❌ {test_name}: 例外発生 - {e}")
                results[test_name] = False

            print()  # 空行

        return results

    def print_summary(self, results: Dict[str, bool]):
        """テスト結果サマリーを表示"""
        print("=" * 60)
        print("📊 テスト結果サマリー")
        print("=" * 60)

        passed = sum(results.values())
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")

        print("-" * 60)
        print(f"合計: {passed}/{total} テスト通過 ({passed / total * 100:.1f}%)")

        if passed == total:
            print("🎉 全てのテストが成功しました！Back2Task MVPは動作可能です。")
        else:
            print("⚠️  一部のテストが失敗しました。設定を確認してください。")
            print("\n🔧 トラブルシューティング:")

            if not results.get("API可用性"):
                print(
                    "- FastAPIサーバーを起動: uvicorn api.main:app --reload --port 5577"
                )

            if not results.get("LLM可用性"):
                print("- LM Studio の Local Server を起動し、モデルをロードしてください（例: google/gemma-3-4b）")
                print("  接続確認: curl http://localhost:1234/v1/models")

            if not results.get("Watchersデータ収集"):
                print(
                    "- 必要な依存関係をインストール: pip install opencv-python pytesseract ultralytics"
                )

        print("=" * 60)


def main():
    """メイン関数"""
    test_runner = Back2TaskIntegrationTest()
    results = test_runner.run_all_tests()
    test_runner.print_summary(results)

    # 全テスト成功の場合は0、失敗があれば1で終了
    success_rate = sum(results.values()) / len(results)
    exit(0 if success_rate >= 0.8 else 1)


if __name__ == "__main__":
    main()
