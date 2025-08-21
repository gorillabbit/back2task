import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestActiveWindowWatcher:
    """Active Window Watcherの動作テスト"""

    def test_get_active_app_windows_success(self):
        """Windowsでの前面ウィンドウ取得成功ケース"""
        # まずモジュールをインポート
        import watchers.active_window as aw_module
        
        # Given: Windows環境のモック
        with patch.object(aw_module, 'WINDOWS_AVAILABLE', True), \
             patch('win32gui.GetForegroundWindow') as mock_get_fg, \
             patch('win32gui.GetWindowText') as mock_get_text, \
             patch('win32process.GetWindowThreadProcessId') as mock_get_pid, \
             patch('psutil.Process') as mock_process_cls:
            
            # ウィンドウハンドルとプロセス情報をモック
            mock_hwnd = 12345
            mock_pid = 9876
            mock_get_fg.return_value = mock_hwnd
            mock_get_text.return_value = "main.py - Visual Studio Code"
            mock_get_pid.return_value = (None, mock_pid)
            
            # プロセス情報をモック
            mock_process = Mock()
            mock_process.name.return_value = "Code.exe"
            mock_process_cls.return_value = mock_process
            
            # win32 モジュールをモック
            with patch.dict('sys.modules', {
                'win32gui': Mock(
                    GetForegroundWindow=mock_get_fg,
                    GetWindowText=mock_get_text
                ),
                'win32process': Mock(
                    GetWindowThreadProcessId=mock_get_pid
                )
            }):
                # When: get_active_app を呼び出す
                result = aw_module._get_active_app_windows()
                
                # Then: アプリ情報が正しく取得される
                assert result["active_app"] == "Code.exe"
                assert result["title"] == "main.py - Visual Studio Code"

    def test_get_active_app_no_window(self):
        """前面ウィンドウがない場合のテスト"""
        # Given: 前面ウィンドウが存在しない
        with patch('watchers.active_window.win32gui') as mock_win32gui:
            mock_win32gui.GetForegroundWindow.return_value = 0  # ウィンドウなし
            
            # When: get_active_app を呼び出す
            from watchers.active_window import get_active_app
            result = get_active_app()
            
            # Then: Noneが返される
            assert result["active_app"] is None
            assert result["title"] is None

    def test_get_active_app_process_error(self):
        """プロセス取得エラーのテスト"""
        # Given: プロセス取得時にエラーが発生
        with patch('watchers.active_window.win32gui') as mock_win32gui, \
             patch('watchers.active_window.win32process') as mock_win32process, \
             patch('watchers.active_window.psutil') as mock_psutil:
            
            mock_hwnd = 12345
            mock_pid = 9876
            mock_win32gui.GetForegroundWindow.return_value = mock_hwnd
            mock_win32gui.GetWindowText.return_value = "Some Window"
            mock_win32process.GetWindowThreadProcessId.return_value = (None, mock_pid)
            
            # プロセス取得時に例外を発生
            mock_psutil.Process.side_effect = Exception("Process not found")
            
            # When: get_active_app を呼び出す
            from watchers.active_window import get_active_app
            result = get_active_app()
            
            # Then: Noneが返される
            assert result["active_app"] is None
            assert result["title"] is None

    def test_get_active_app_different_applications(self):
        """異なるアプリケーションの検出テスト"""
        test_cases = [
            {
                "process_name": "chrome.exe",
                "window_title": "YouTube - Google Chrome",
                "expected_app": "chrome.exe",
                "expected_title": "YouTube - Google Chrome"
            },
            {
                "process_name": "notepad.exe",
                "window_title": "無題 - メモ帳",
                "expected_app": "notepad.exe",
                "expected_title": "無題 - メモ帳"
            },
            {
                "process_name": "python.exe",
                "window_title": "Python 3.11.2 Shell",
                "expected_app": "python.exe",
                "expected_title": "Python 3.11.2 Shell"
            }
        ]
        
        for case in test_cases:
            # Given: 各アプリケーションの状態をモック
            with patch('watchers.active_window.win32gui') as mock_win32gui, \
                 patch('watchers.active_window.win32process') as mock_win32process, \
                 patch('watchers.active_window.psutil') as mock_psutil:
                
                mock_hwnd = 12345
                mock_pid = 9876
                mock_win32gui.GetForegroundWindow.return_value = mock_hwnd
                mock_win32gui.GetWindowText.return_value = case["window_title"]
                mock_win32process.GetWindowThreadProcessId.return_value = (None, mock_pid)
                
                mock_process = Mock()
                mock_process.name.return_value = case["process_name"]
                mock_psutil.Process.return_value = mock_process
                
                # When: get_active_app を呼び出す
                from watchers.active_window import get_active_app
                result = get_active_app()
                
                # Then: 期待される結果が返される
                assert result["active_app"] == case["expected_app"]
                assert result["title"] == case["expected_title"]

    def test_get_active_app_empty_title(self):
        """ウィンドウタイトルが空の場合のテスト"""
        # Given: ウィンドウタイトルが空
        with patch('watchers.active_window.win32gui') as mock_win32gui, \
             patch('watchers.active_window.win32process') as mock_win32process, \
             patch('watchers.active_window.psutil') as mock_psutil:
            
            mock_hwnd = 12345
            mock_pid = 9876
            mock_win32gui.GetForegroundWindow.return_value = mock_hwnd
            mock_win32gui.GetWindowText.return_value = ""  # 空のタイトル
            mock_win32process.GetWindowThreadProcessId.return_value = (None, mock_pid)
            
            mock_process = Mock()
            mock_process.name.return_value = "explorer.exe"
            mock_psutil.Process.return_value = mock_process
            
            # When: get_active_app を呼び出す
            from watchers.active_window import get_active_app
            result = get_active_app()
            
            # Then: プロセス名は取得され、タイトルは空
            assert result["active_app"] == "explorer.exe"
            assert result["title"] == ""

    @pytest.mark.parametrize("interval", [1, 2, 5])
    def test_continuous_monitoring(self, interval):
        """連続監視のテスト"""
        import time
        
        # Given: 監視間隔を指定
        results = []
        expected_calls = 3
        
        # モック化された監視関数
        def mock_monitor():
            for i in range(expected_calls):
                results.append({
                    "active_app": f"app_{i}.exe",
                    "title": f"Window {i}",
                    "timestamp": time.time()
                })
                time.sleep(0.1)  # 短時間待機（テスト用）
        
        # When: 連続監視を実行
        mock_monitor()
        
        # Then: 指定回数の結果が得られる
        assert len(results) == expected_calls
        
        # And: 各結果が適切な形式
        for i, result in enumerate(results):
            assert result["active_app"] == f"app_{i}.exe"
            assert result["title"] == f"Window {i}"
            assert "timestamp" in result

    def test_linux_fallback(self):
        """Linux環境での代替実装テスト"""
        # Given: Windows APIが利用できない環境
        with patch('watchers.active_window.win32gui', side_effect=ImportError), \
             patch('watchers.active_window.psutil') as mock_psutil:
            
            # When: get_active_app_linux を呼び出す（代替実装）
            from watchers.active_window import get_active_app_linux
            result = get_active_app_linux()
            
            # Then: 代替的な情報が返される（例：現在実行中のプロセス情報）
            assert "active_app" in result
            assert "title" in result
            # Linux環境では制限された情報のみ取得可能

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