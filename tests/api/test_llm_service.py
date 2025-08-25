import pytest
import json
import requests
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestLLMService:
    """LLMサービスのテスト"""

    @pytest.fixture
    def llm_service(self):
        """テスト用のLLMサービス"""
        from api.services.llm import LLMService

        return LLMService(
            base_url="http://localhost:1234", model_name="google/gemma-3-4b"
        )

    @pytest.fixture
    def mock_observations(self):
        """テスト用の観測データ"""
        return {
            "active_app": "Code.exe",
            "title": "main.py - VSCode",
            "url": "",
            "idle_ms": 1000,
            "ocr": "def function_name():",
            "phone_detected": False,
            "phone": "",
        }

    @pytest.fixture
    def distracted_observations(self):
        """脱線している観測データ"""
        return {
            "active_app": "chrome.exe",
            "title": "YouTube - Google Chrome",
            "url": "https://youtube.com/watch",
            "idle_ms": 500,
            "ocr": "おすすめ動画 登録者数",
            "phone_detected": False,
            "phone": "",
        }

    @pytest.fixture
    def phone_distracted_observations(self):
        """スマホ脱線の観測データ"""
        return {
            "active_app": "Code.exe",
            "title": "main.py - VSCode",
            "url": "",
            "idle_ms": 1000,
            "ocr": "def function_name():",
            "phone_detected": True,
            "phone": "jp.youtube",
        }

    def test_llm_service_initialization(self, llm_service):
        """LLMサービスの初期化テスト"""
        assert llm_service.base_url == "http://localhost:1234"
        assert llm_service.model_name == "google/gemma-3-4b"
        assert llm_service.timeout == 20.0
        assert llm_service.chat_url == "http://localhost:1234/v1/chat/completions"
        assert len(llm_service.system_prompt) > 0

    def test_availability_check_success(self, llm_service):
        """LLM可用性チェック（成功）"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert llm_service.is_available() is True
            mock_get.assert_called_once_with(
                "http://localhost:1234/v1/models", timeout=5
            )

    def test_availability_check_failure(self, llm_service):
        """LLM可用性チェック（失敗）"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            assert llm_service.is_available() is False

    def test_build_context_prompt(self, llm_service, mock_observations):
        """コンテキストプロンプト構築テスト"""
        task = "コーディング作業"
        context = llm_service._build_context_prompt(task, mock_observations)

        assert "コーディング作業" in context
        assert "Code.exe" in context
        assert "main.py - VSCode" in context
        assert "active" in context
        assert "no phone" in context
        assert "def function_name():" in context

    def test_fallback_policy_productive(self, llm_service, mock_observations):
        """フォールバック政策（生産的）"""
        policy = llm_service._fallback_policy(mock_observations)

        assert policy.action == "quiet"
        assert policy.reason == "Productive activity"
        assert policy.confidence > 0.5

    def test_fallback_policy_strong_distraction(
        self, llm_service, distracted_observations
    ):
        """フォールバック政策（強い脱線）"""
        policy = llm_service._fallback_policy(distracted_observations)

        assert policy.action == "strong_nudge"
        assert "distraction" in policy.reason.lower()
        assert policy.tip is not None
        assert policy.confidence > 0.7

    def test_fallback_policy_phone_distraction(
        self, llm_service, phone_distracted_observations
    ):
        """フォールバック政策（スマホ脱線）"""
        policy = llm_service._fallback_policy(phone_distracted_observations)

        assert policy.action == "strong_nudge"
        assert "phone" in policy.reason.lower()
        assert policy.confidence > 0.8

    def test_fallback_policy_idle(self, llm_service):
        """フォールバック政策（アイドル状態）"""
        idle_observations = {
            "active_app": "explorer.exe",
            "title": "Desktop",
            "url": "",
            "idle_ms": 400000,  # 6分40秒
            "ocr": "",
            "phone_detected": False,
            "phone": "",
        }

        policy = llm_service._fallback_policy(idle_observations)

        assert policy.action == "gentle_nudge"
        assert "idle" in policy.reason.lower()
        assert policy.tip is not None

    def test_decide_nudging_policy_llm_unavailable(
        self, llm_service, mock_observations
    ):
        """LLM利用不可時のnudging決定"""
        with patch.object(llm_service, "is_available", return_value=False):
            policy = llm_service.decide_nudging_policy(
                "テストタスク", mock_observations
            )

            # フォールバック政策が使われる
            assert policy.action in ["quiet", "gentle_nudge", "strong_nudge"]
            assert isinstance(policy.reason, str)
            assert isinstance(policy.confidence, float)

    def test_decide_nudging_policy_llm_success(self, llm_service, mock_observations):
        """LLM利用成功時のnudging決定"""
        mock_response_data = {
            "action": "quiet",
            "reason": "Productive coding",
            "tip": "Keep up the good work!",
        }

        with (
            patch.object(llm_service, "is_available", return_value=True),
            patch("requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": json.dumps(mock_response_data)}}]
            }
            mock_post.return_value = mock_response

            policy = llm_service.decide_nudging_policy(
                "テストタスク", mock_observations
            )

            assert policy.action == "quiet"
            assert policy.reason == "Productive coding"
            assert policy.tip == "Keep up the good work!"
            assert policy.confidence == 0.8

    def test_decide_nudging_policy_llm_json_parse_error(
        self, llm_service, mock_observations
    ):
        """LLM JSONパースエラー時の処理"""
        with (
            patch.object(llm_service, "is_available", return_value=True),
            patch("requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Invalid JSON response"}}]
            }
            mock_post.return_value = mock_response

            policy = llm_service.decide_nudging_policy(
                "テストタスク", mock_observations
            )

            # フォールバックが使われる
            assert policy.action in ["quiet", "gentle_nudge", "strong_nudge"]

    def test_decide_nudging_policy_llm_api_error(self, llm_service, mock_observations):
        """LLM APIエラー時の処理"""
        with (
            patch.object(llm_service, "is_available", return_value=True),
            patch("requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            policy = llm_service.decide_nudging_policy(
                "テストタスク", mock_observations
            )

            # フォールバックが使われる
            assert policy.action in ["quiet", "gentle_nudge", "strong_nudge"]

    def test_decide_nudging_policy_timeout(self, llm_service, mock_observations):
        """LLM タイムアウト時の処理"""
        with (
            patch.object(llm_service, "is_available", return_value=True),
            patch("requests.post") as mock_post,
        ):
            mock_post.side_effect = requests.exceptions.Timeout()

            policy = llm_service.decide_nudging_policy(
                "テストタスク", mock_observations
            )

            # フォールバックが使われる
            assert policy.action in ["quiet", "gentle_nudge", "strong_nudge"]

    def test_generate_task_suggestions_llm_unavailable(self, llm_service):
        """LLM利用不可時のタスク提案"""
        with patch.object(llm_service, "is_available", return_value=False):
            suggestions = llm_service.generate_task_suggestions("レポート作成")

            assert "subtasks" in suggestions
            assert "encouragement" in suggestions
            assert "estimated_minutes" in suggestions
            assert isinstance(suggestions["subtasks"], list)
            assert len(suggestions["subtasks"]) > 0

    def test_generate_task_suggestions_llm_success(self, llm_service):
        """LLM利用成功時のタスク提案"""
        mock_response_data = {
            "subtasks": [
                "Research the topic",
                "Create an outline",
                "Write first draft",
                "Review and edit",
            ],
            "encouragement": "Break it down into steps!",
            "estimated_minutes": 15,
        }

        with (
            patch.object(llm_service, "is_available", return_value=True),
            patch("requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": json.dumps(mock_response_data)}}]
            }
            mock_post.return_value = mock_response

            suggestions = llm_service.generate_task_suggestions("レポート作成")

            assert suggestions["subtasks"] == mock_response_data["subtasks"]
            assert suggestions["encouragement"] == mock_response_data["encouragement"]
            assert (
                suggestions["estimated_minutes"]
                == mock_response_data["estimated_minutes"]
            )

    def test_rate_limiting(self, llm_service):
        """レート制限テスト"""
        import time

        # 初回呼び出し
        start_time = time.time()
        llm_service._rate_limit()
        first_call_time = time.time() - start_time

        # 直後の呼び出し（レート制限が働く）
        start_time = time.time()
        llm_service._rate_limit()
        second_call_time = time.time() - start_time

        # 2回目の呼び出しで待機時間が発生する
        assert (
            second_call_time >= llm_service.min_call_interval - 0.1
        )  # 少し余裕を持たせる

    def test_get_model_info_success(self, llm_service):
        """モデル情報取得（成功）"""
        mock_model_data = {
            "object": "list",
            "data": [
                {
                    "id": "google/gemma-3-4b",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai",
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_model_data
            mock_get.return_value = mock_response

            info = llm_service.get_model_info()

            assert info == mock_model_data

    def test_get_model_info_failure(self, llm_service):
        """モデル情報取得（失敗）"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("API Error")

            info = llm_service.get_model_info()

            # フォールバック情報が返される
            assert "data" in info
            assert len(info["data"]) > 0
            assert info["data"][0]["id"] == "google/gemma-3-4b"

    def test_convenience_functions(self):
        """便利関数のテスト"""
        from api.services.llm import create_llm_service, decide_nudging_policy

        # create_llm_service
        service = create_llm_service("http://test:1234")
        assert service.base_url == "http://test:1234"

        # decide_nudging_policy
        observations = {
            "active_app": "test.exe",
            "title": "Test",
            "url": "",
            "idle_ms": 1000,
            "ocr": "productive content",
            "phone_detected": False,
            "phone": "",
        }

        with patch("api.services.llm.LLMService") as mock_service_class:
            mock_service = Mock()
            mock_policy = Mock()
            mock_policy.action = "quiet"
            mock_service.decide_nudging_policy.return_value = mock_policy
            mock_service_class.return_value = mock_service

            policy = decide_nudging_policy("test task", observations)

            assert policy.action == "quiet"
