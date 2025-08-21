import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestActiveWindowWatcherSimple:
    """Active Window Watcherの簡単なテスト"""

    def test_get_active_app_linux(self):
        """Linux環境での代替実装テスト"""
        # Given: Linux環境
        import watchers.active_window as aw
        
        # When: Linux版を呼び出す
        result = aw.get_active_app_linux()
        
        # Then: 適切な形式で結果が返される
        assert isinstance(result, dict)
        assert "active_app" in result
        assert "title" in result

    def test_data_format_consistency(self):
        """データ形式の一貫性テスト"""
        # Given: 様々なシナリオ
        scenarios = [
            {"app": "Code.exe", "title": "main.py - VSCode"},
            {"app": None, "title": None},  # エラーケース
            {"app": "chrome.exe", "title": ""},  # 空のタイトル
        ]
        
        for scenario in scenarios:
            # When: 結果を生成
            result = {
                "active_app": scenario["app"],
                "title": scenario["title"]
            }
            
            # Then: 期待される形式に準拠
            assert isinstance(result, dict)
            assert "active_app" in result
            assert "title" in result
            assert result["active_app"] is None or isinstance(result["active_app"], str)
            assert result["title"] is None or isinstance(result["title"], str)

    def test_is_system_process(self):
        """システムプロセス判定テスト"""
        import watchers.active_window as aw
        
        # Given: システムプロセス名
        system_processes = ["systemd", "kthreadd", "dbus-daemon", "NetworkManager"]
        user_processes = ["chrome", "firefox", "code", "python"]
        
        # When/Then: システムプロセスが正しく判定される
        for proc in system_processes:
            assert aw._is_system_process(proc) is True
            
        for proc in user_processes:
            assert aw._is_system_process(proc) is False

    def test_get_active_app_fallback(self):
        """フォールバック実装テスト"""
        import watchers.active_window as aw
        
        # When: フォールバック実装を呼び出す
        result = aw._get_active_app_fallback()
        
        # Then: 適切な形式で結果が返される
        assert isinstance(result, dict)
        assert "active_app" in result
        assert "title" in result

    def test_get_active_app_main_function(self):
        """メイン関数のテスト"""
        import watchers.active_window as aw
        
        # When: メイン関数を呼び出す
        result = aw.get_active_app()
        
        # Then: 適切な形式で結果が返される
        assert isinstance(result, dict)
        assert "active_app" in result
        assert "title" in result
        
        # Linux環境では active_app または title に値があるか、両方None
        if result["active_app"] is not None:
            assert isinstance(result["active_app"], str)
        if result["title"] is not None:
            assert isinstance(result["title"], str)

    @pytest.mark.parametrize("interval", [0.1, 0.5, 1.0])
    def test_monitor_function_structure(self, interval):
        """モニター関数の構造テスト"""
        import watchers.active_window as aw
        
        # Given: コールバック関数をモック
        callback = Mock()
        results = []
        
        def test_callback(result):
            results.append(result)
            if len(results) >= 2:  # 2回呼ばれたら停止
                raise KeyboardInterrupt()
        
        # When: モニター関数を短時間実行
        try:
            aw.monitor_active_window(interval=interval, callback=test_callback)
        except KeyboardInterrupt:
            pass  # 期待される終了
        
        # Then: コールバックが呼ばれている
        assert len(results) >= 1
        for result in results:
            assert isinstance(result, dict)
            assert "active_app" in result
            assert "title" in result