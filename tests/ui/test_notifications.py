import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestNotificationService:
    """通知サービスのテスト"""
    
    @pytest.fixture
    def notification_service(self):
        """テスト用の通知サービス"""
        from ui.notifications import NotificationService, NotificationConfig
        config = NotificationConfig(
            enable_toast=True,
            enable_sound=True,
            enable_flash=False,
            toast_duration=3
        )
        return NotificationService(config)
    
    @pytest.fixture
    def mock_platform_linux(self):
        """Linuxプラットフォームをモック"""
        with patch('platform.system', return_value='Linux'):
            yield
    
    @pytest.fixture
    def mock_platform_windows(self):
        """Windowsプラットフォームをモック"""
        with patch('platform.system', return_value='Windows'):
            yield
    
    def test_notification_service_initialization(self, notification_service):
        """通知サービスの初期化テスト"""
        assert notification_service.config.enable_toast is True
        assert notification_service.config.enable_sound is True
        assert notification_service.config.enable_flash is False
        assert notification_service.config.toast_duration == 3
        assert len(notification_service.notification_history) == 0
    
    def test_platform_detection(self):
        """プラットフォーム検出テスト"""
        from ui.notifications import NotificationService
        
        # デフォルト初期化でプラットフォームが設定される
        service = NotificationService()
        assert service.platform in ['Linux', 'Windows', 'Darwin']
    
    def test_linux_initialization(self, mock_platform_linux):
        """Linux環境での初期化テスト"""
        from ui.notifications import NotificationService
        
        with patch('subprocess.run') as mock_run:
            # notify-send が利用可能
            mock_run.return_value.returncode = 0
            
            service = NotificationService()
            assert service.platform == 'Linux'
            # 実際の利用可能性は環境依存
    
    def test_windows_initialization(self, mock_platform_windows):
        """Windows環境での初期化テスト"""
        from ui.notifications import NotificationService
        
        # WinRT が利用できない場合
        with patch.dict('sys.modules', {'winrt.windows.ui.notifications': None}):
            service = NotificationService()
            assert service.platform == 'Windows'
    
    def test_rate_limiting(self, notification_service):
        """レート制限テスト"""
        from ui.notifications import NotificationLevel
        
        # 初回通知は成功
        result1 = notification_service._rate_limit_check()
        assert result1 is True
        
        # 直後の通知は制限される
        result2 = notification_service._rate_limit_check()
        assert result2 is False
        
        # 時間経過後は通知可能
        notification_service.last_notification_time = time.time() - 2.0
        result3 = notification_service._rate_limit_check()
        assert result3 is True
    
    def test_notification_history(self, notification_service):
        """通知履歴のテスト"""
        from ui.notifications import NotificationLevel
        
        # 通知を送信（実際の通知は無効化）
        with patch.object(notification_service, '_send_toast', return_value=True):
            notification_service.notify("Test", "Message", NotificationLevel.INFO)
        
        # 履歴が記録される
        history = notification_service.get_notification_history()
        assert len(history) == 1
        assert history[0]["title"] == "Test"
        assert history[0]["message"] == "Message"
        assert history[0]["level"] == "info"
    
    def test_notification_levels(self, notification_service):
        """通知レベルのテスト"""
        from ui.notifications import NotificationLevel
        
        test_cases = [
            (NotificationLevel.INFO, "info"),
            (NotificationLevel.WARNING, "warning"),
            (NotificationLevel.URGENT, "urgent")
        ]
        
        with patch.object(notification_service, '_send_toast', return_value=True), \
             patch.object(notification_service, '_play_sound'), \
             patch.object(notification_service, '_flash_screen'):
            
            for level, expected_value in test_cases:
                notification_service.notify("Test", "Message", level)
                
                history = notification_service.get_notification_history(1)
                assert history[0]["level"] == expected_value
    
    def test_linux_toast_notification(self, notification_service, mock_platform_linux):
        """Linux Toast通知のテスト"""
        from ui.notifications import NotificationLevel
        
        # notify-send が利用可能な場合
        notification_service.toast_available = True
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            result = notification_service._send_linux_notification(
                "Test Title", "Test Message", NotificationLevel.INFO
            )
            
            assert result is True
            mock_run.assert_called()
            
            # コマンド引数の確認
            call_args = mock_run.call_args[0][0]
            assert "notify-send" in call_args
            assert "Test Title" in call_args
            assert "Test Message" in call_args
    
    def test_linux_toast_notification_failure(self, notification_service, mock_platform_linux):
        """Linux Toast通知の失敗テスト"""
        from ui.notifications import NotificationLevel
        
        notification_service.toast_available = True
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")
            
            result = notification_service._send_linux_notification(
                "Test Title", "Test Message", NotificationLevel.INFO
            )
            
            assert result is False
    
    def test_fallback_console_notification(self, notification_service):
        """フォールバック（コンソール）通知のテスト"""
        from ui.notifications import NotificationLevel
        
        # Toast が利用できない場合
        notification_service.toast_available = False
        
        with patch('builtins.print') as mock_print:
            result = notification_service._send_toast(
                "Test Title", "Test Message", NotificationLevel.WARNING
            )
            
            assert result is True
            mock_print.assert_called()
            
            # コンソール出力の確認
            call_args = str(mock_print.call_args)
            assert "WARNING" in call_args
            assert "Test Title" in call_args
            assert "Test Message" in call_args
    
    def test_sound_configuration(self, notification_service):
        """音設定のテスト"""
        from ui.notifications import NotificationLevel
        
        with patch.object(notification_service, '_send_toast', return_value=True), \
             patch.object(notification_service, '_play_sound') as mock_sound:
            
            # INFO レベルでは音が鳴らない
            notification_service.notify("Test", "Message", NotificationLevel.INFO)
            mock_sound.assert_not_called()
            
            # WARNING レベルでは音が鳴る
            notification_service.notify("Test", "Message", NotificationLevel.WARNING)
            mock_sound.assert_called_once()
    
    def test_flash_configuration(self, notification_service):
        """フラッシュ設定のテスト"""
        from ui.notifications import NotificationLevel
        
        # フラッシュを有効化
        notification_service.config.enable_flash = True
        notification_service.flash_available = True
        
        with patch.object(notification_service, '_send_toast', return_value=True), \
             patch.object(notification_service, '_flash_screen') as mock_flash:
            
            # URGENT レベルでのみフラッシュ
            notification_service.notify("Test", "Message", NotificationLevel.INFO)
            mock_flash.assert_not_called()
            
            notification_service.notify("Test", "Message", NotificationLevel.URGENT)
            mock_flash.assert_called_once()
    
    def test_notification_override_settings(self, notification_service):
        """通知設定のオーバーライドテスト"""
        from ui.notifications import NotificationLevel
        
        with patch.object(notification_service, '_send_toast', return_value=True), \
             patch.object(notification_service, '_play_sound') as mock_sound, \
             patch.object(notification_service, '_flash_screen') as mock_flash:
            
            # 明示的に音とフラッシュを指定
            notification_service.notify(
                "Test", "Message", NotificationLevel.INFO,
                sound=True, flash=True
            )
            
            # 設定に関係なく実行される
            mock_sound.assert_called()
            mock_flash.assert_called()
    
    def test_capabilities_reporting(self, notification_service):
        """機能対応状況のテスト"""
        capabilities = notification_service.get_capabilities()
        
        assert "toast" in capabilities
        assert "sound" in capabilities
        assert "flash" in capabilities
        assert "platform" in capabilities
        assert isinstance(capabilities["toast"], bool)
        assert isinstance(capabilities["sound"], bool)
        assert isinstance(capabilities["flash"], bool)
        assert isinstance(capabilities["platform"], str)
    
    def test_history_size_limit(self, notification_service):
        """履歴サイズ制限のテスト"""
        from ui.notifications import NotificationLevel
        
        # 履歴サイズを小さく設定
        notification_service.max_history = 3
        
        with patch.object(notification_service, '_send_toast', return_value=True):
            # 5回通知を送信
            for i in range(5):
                notification_service.notify(f"Test {i}", "Message", NotificationLevel.INFO)
        
        # 履歴が制限される
        history = notification_service.get_notification_history()
        assert len(history) == 3
        
        # 最新の通知が保持される
        assert "Test 4" in history[-1]["title"]
    
    def test_convenience_functions(self):
        """便利関数のテスト"""
        from ui.notifications import (
            notify, notify_gentle_nudge, notify_strong_nudge, 
            notify_task_complete, get_notification_service
        )
        
        # get_notification_service
        service1 = get_notification_service()
        service2 = get_notification_service()
        assert service1 is service2  # シングルトン的動作
        
        # 便利関数
        with patch.object(service1, 'notify', return_value=True) as mock_notify:
            notify("Test", "Message")
            mock_notify.assert_called()
            
            notify_gentle_nudge("Gentle message")
            mock_notify.assert_called()
            
            notify_strong_nudge("Strong message")
            mock_notify.assert_called()
            
            notify_task_complete("Test task")
            mock_notify.assert_called()
    
    def test_notification_config(self):
        """通知設定のテスト"""
        from ui.notifications import NotificationConfig
        
        # デフォルト設定
        config = NotificationConfig()
        assert config.enable_toast is True
        assert config.enable_sound is True
        assert config.enable_flash is False
        assert config.toast_duration == 5
        assert config.flash_duration == 0.5
        assert config.flash_count == 3
        
        # カスタム設定
        config = NotificationConfig(
            enable_toast=False,
            enable_sound=False,
            enable_flash=True,
            toast_duration=10
        )
        assert config.enable_toast is False
        assert config.enable_sound is False
        assert config.enable_flash is True
        assert config.toast_duration == 10