import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_state():
    """テスト用のモック状態"""
    return {
        "current_task": None,
        "productive": False,
        "done": None,
        "config": {"tick_sec": 2, "slip_tolerance": 5},
    }


@pytest.fixture
def mock_session_data():
    """テスト用のセッションデータ"""
    return {
        "id": "test_task",
        "goal": 25 * 60,  # 25分 = 1500秒
        "accum": 0,
        "last_obs": {},
        "started_at": 1234567890.0
    }


@pytest.fixture
def productive_event():
    """生産的なイベントデータ"""
    return {
        "active_app": "Code.exe",
        "title": "main.py - VSCode",
        "url": "",
        "idle_ms": 1000,
        "ocr": "def function_name():",
        "phone": "",
        "phone_detected": False
    }


@pytest.fixture
def distracted_event():
    """脱線イベントデータ"""
    return {
        "active_app": "chrome.exe",
        "title": "YouTube - Google Chrome",
        "url": "https://youtube.com",
        "idle_ms": 500,
        "ocr": "おすすめ動画",
        "phone": "",
        "phone_detected": False
    }


@pytest.fixture
def phone_distracted_event():
    """スマホ脱線イベントデータ"""
    return {
        "active_app": "Code.exe",
        "title": "main.py - VSCode",
        "url": "",
        "idle_ms": 1000,
        "ocr": "def function_name():",
        "phone": "jp.youtube",
        "phone_detected": True
    }


@pytest.fixture
def idle_event():
    """アイドル状態イベントデータ"""
    return {
        "active_app": "Code.exe",
        "title": "main.py - VSCode",
        "url": "",
        "idle_ms": 10000,  # 10秒アイドル
        "ocr": "def function_name():",
        "phone": "",
        "phone_detected": False
    }


@pytest.fixture
def mock_llm_service():
    """LLMサービスのモック"""
    mock = Mock()
    mock.decide = Mock(return_value={
        "action": "gentle_nudge",
        "reason": "test reason",
        "tip": "test tip"
    })
    return mock


@pytest.fixture
def mock_notification_service():
    """通知サービスのモック"""
    mock = Mock()
    mock.notify = Mock()
    return mock


@pytest.fixture
def event_loop():
    """非同期テスト用のイベントループ"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()