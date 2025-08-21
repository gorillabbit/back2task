import platform
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class NotificationLevel(Enum):
    """通知レベル"""
    INFO = "info"
    WARNING = "warning" 
    URGENT = "urgent"


@dataclass
class NotificationConfig:
    """通知設定"""
    enable_toast: bool = True
    enable_sound: bool = True
    enable_flash: bool = False
    toast_duration: int = 5  # 秒
    flash_duration: float = 0.5  # 秒
    flash_count: int = 3


class NotificationService:
    """マルチプラットフォーム通知サービス"""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Args:
            config: 通知設定
        """
        self.config = config or NotificationConfig()
        self.platform = platform.system()
        
        # プラットフォーム固有の初期化
        self._init_platform_specific()
        
        # 通知履歴
        self.notification_history = []
        self.max_history = 100
        
        # レート制限
        self.last_notification_time = 0
        self.min_notification_interval = 1.0  # 秒
        
    def _init_platform_specific(self):
        """プラットフォーム固有の初期化"""
        self.toast_available = False
        self.sound_available = False
        self.flash_available = False
        
        if self.platform == "Windows":
            self._init_windows()
        elif self.platform == "Linux":
            self._init_linux()
        elif self.platform == "Darwin":  # macOS
            self._init_macos()
    
    def _init_windows(self):
        """Windows固有の初期化"""
        try:
            # WinRT for Toast notifications
            from winrt.windows.ui.notifications import ToastNotificationManager
            from winrt.windows.data.xml.dom import XmlDocument
            self.toast_available = True
            self._ToastNotificationManager = ToastNotificationManager
            self._XmlDocument = XmlDocument
        except ImportError:
            print("Windows toast notifications not available")
        
        try:
            # Windows API for sound and flash
            import winsound
            self.sound_available = True
            self._winsound = winsound
        except ImportError:
            print("Windows sound not available")
        
        # Flash (画面フラッシュ) は Windows API で実装可能
        self.flash_available = True
    
    def _init_linux(self):
        """Linux固有の初期化"""
        try:
            # notify-send for desktop notifications
            import subprocess
            result = subprocess.run(["which", "notify-send"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.toast_available = True
        except Exception:
            pass
        
        try:
            # Play sound using paplay/aplay
            import subprocess
            for cmd in ["paplay", "aplay", "play"]:
                result = subprocess.run(["which", cmd], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    self.sound_available = True
                    self._sound_cmd = cmd
                    break
        except Exception:
            pass
        
        # Flash can be implemented via X11
        try:
            import subprocess
            result = subprocess.run(["which", "xset"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.flash_available = True
        except Exception:
            pass
    
    def _init_macos(self):
        """macOS固有の初期化"""
        try:
            # osascript for notifications
            import subprocess
            result = subprocess.run(["which", "osascript"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.toast_available = True
        except Exception:
            pass
        
        try:
            # afplay for sound
            import subprocess
            result = subprocess.run(["which", "afplay"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.sound_available = True
        except Exception:
            pass
    
    def _rate_limit_check(self) -> bool:
        """レート制限チェック"""
        now = time.time()
        if now - self.last_notification_time < self.min_notification_interval:
            return False
        self.last_notification_time = now
        return True
    
    def notify(self, 
               title: str, 
               message: str, 
               level: NotificationLevel = NotificationLevel.INFO,
               sound: Optional[bool] = None,
               flash: Optional[bool] = None) -> bool:
        """
        通知を送信
        
        Args:
            title: 通知タイトル
            message: 通知メッセージ
            level: 通知レベル
            sound: 音を鳴らすか（Noneの場合は設定に従う）
            flash: 画面をフラッシュするか（Noneの場合は設定に従う）
            
        Returns:
            bool: 通知送信成功時True
        """
        # レート制限チェック
        if not self._rate_limit_check():
            return False
        
        # 設定のオーバーライド
        play_sound = sound if sound is not None else self.config.enable_sound
        do_flash = flash if flash is not None else self.config.enable_flash
        
        # 通知履歴に記録
        notification_record = {
            "timestamp": time.time(),
            "title": title,
            "message": message,
            "level": level.value,
            "sound": play_sound,
            "flash": do_flash
        }
        self.notification_history.append(notification_record)
        
        # 履歴サイズ制限
        if len(self.notification_history) > self.max_history:
            self.notification_history.pop(0)
        
        success = True
        
        # Toast通知
        if self.config.enable_toast:
            success &= self._send_toast(title, message, level)
        
        # 音通知
        if play_sound and level != NotificationLevel.INFO:
            self._play_sound(level)
        
        # フラッシュ通知
        if do_flash and level == NotificationLevel.URGENT:
            self._flash_screen()
        
        return success
    
    def _send_toast(self, title: str, message: str, level: NotificationLevel) -> bool:
        """Toast通知を送信"""
        if not self.toast_available:
            print(f"[{level.value.upper()}] {title}: {message}")
            return True
        
        try:
            if self.platform == "Windows":
                return self._send_windows_toast(title, message, level)
            elif self.platform == "Linux":
                return self._send_linux_notification(title, message, level)
            elif self.platform == "Darwin":
                return self._send_macos_notification(title, message, level)
        except Exception as e:
            print(f"Toast notification error: {e}")
            # フォールバック: コンソール出力
            print(f"[{level.value.upper()}] {title}: {message}")
            return False
        
        return False
    
    def _send_windows_toast(self, title: str, message: str, level: NotificationLevel) -> bool:
        """Windows Toast通知"""
        try:
            # レベルに応じたアイコン設定
            icon_type = {
                NotificationLevel.INFO: "",
                NotificationLevel.WARNING: "⚠️",
                NotificationLevel.URGENT: "🚨"
            }.get(level, "")
            
            display_title = f"{icon_type} {title}".strip()
            
            xml_template = f"""
            <toast>
                <visual>
                    <binding template='ToastGeneric'>
                        <text>{display_title}</text>
                        <text>{message}</text>
                    </binding>
                </visual>
                <audio src='ms-winsoundevent:Notification.Default' />
            </toast>
            """
            
            doc = self._XmlDocument()
            doc.load_xml(xml_template)
            
            notifier = self._ToastNotificationManager.create_toast_notifier("Back2Task")
            toast = self._ToastNotificationManager.ToastNotification(doc)
            
            notifier.show(toast)
            return True
            
        except Exception as e:
            print(f"Windows toast error: {e}")
            return False
    
    def _send_linux_notification(self, title: str, message: str, level: NotificationLevel) -> bool:
        """Linux desktop notification"""
        try:
            import subprocess
            
            # レベルに応じた設定
            urgency_map = {
                NotificationLevel.INFO: "low",
                NotificationLevel.WARNING: "normal", 
                NotificationLevel.URGENT: "critical"
            }
            
            icon_map = {
                NotificationLevel.INFO: "dialog-information",
                NotificationLevel.WARNING: "dialog-warning",
                NotificationLevel.URGENT: "dialog-error"
            }
            
            cmd = [
                "notify-send",
                "--urgency", urgency_map[level],
                "--icon", icon_map[level],
                "--expire-time", str(self.config.toast_duration * 1000),
                title,
                message
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Linux notification error: {e}")
            return False
    
    def _send_macos_notification(self, title: str, message: str, level: NotificationLevel) -> bool:
        """macOS notification"""
        try:
            import subprocess
            
            script = f'''
            display notification "{message}" with title "{title}"
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
            
        except Exception as e:
            print(f"macOS notification error: {e}")
            return False
    
    def _play_sound(self, level: NotificationLevel):
        """音を再生"""
        if not self.sound_available:
            return
        
        try:
            if self.platform == "Windows":
                self._play_windows_sound(level)
            elif self.platform == "Linux":
                self._play_linux_sound(level)
            elif self.platform == "Darwin":
                self._play_macos_sound(level)
        except Exception as e:
            print(f"Sound play error: {e}")
    
    def _play_windows_sound(self, level: NotificationLevel):
        """Windows音再生"""
        sound_map = {
            NotificationLevel.INFO: self._winsound.MB_OK,
            NotificationLevel.WARNING: self._winsound.MB_ICONEXCLAMATION,
            NotificationLevel.URGENT: self._winsound.MB_ICONHAND
        }
        
        self._winsound.MessageBeep(sound_map[level])
    
    def _play_linux_sound(self, level: NotificationLevel):
        """Linux音再生"""
        # システム音を再生（/usr/share/sounds/から）
        import subprocess
        
        sound_files = {
            NotificationLevel.INFO: "/usr/share/sounds/alsa/Front_Left.wav",
            NotificationLevel.WARNING: "/usr/share/sounds/alsa/Side_Left.wav", 
            NotificationLevel.URGENT: "/usr/share/sounds/alsa/Rear_Left.wav"
        }
        
        sound_file = sound_files.get(level)
        if sound_file:
            try:
                subprocess.run([self._sound_cmd, sound_file], 
                             capture_output=True, timeout=3)
            except Exception:
                # フォールバック: beep
                subprocess.run(["pactl", "upload-sample", "/usr/share/sounds/alsa/Front_Left.wav", "bell"], 
                             capture_output=True)
    
    def _play_macos_sound(self, level: NotificationLevel):
        """macOS音再生"""
        import subprocess
        
        sound_map = {
            NotificationLevel.INFO: "Glass",
            NotificationLevel.WARNING: "Sosumi",
            NotificationLevel.URGENT: "Basso"
        }
        
        sound_name = sound_map[level]
        subprocess.run(["afplay", f"/System/Library/Sounds/{sound_name}.aiff"],
                      capture_output=True, timeout=3)
    
    def _flash_screen(self):
        """画面をフラッシュ"""
        if not self.flash_available:
            return
        
        try:
            if self.platform == "Windows":
                self._flash_windows_screen()
            elif self.platform == "Linux":
                self._flash_linux_screen()
            elif self.platform == "Darwin":
                self._flash_macos_screen()
        except Exception as e:
            print(f"Screen flash error: {e}")
    
    def _flash_windows_screen(self):
        """Windows画面フラッシュ"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # GetDC and FlashWindow APIs
            user32 = ctypes.windll.user32
            
            # デスクトップウィンドウを取得してフラッシュ
            hwnd = user32.GetDesktopWindow()
            
            for _ in range(self.config.flash_count):
                user32.FlashWindow(hwnd, True)
                time.sleep(self.config.flash_duration)
                
        except Exception as e:
            print(f"Windows flash error: {e}")
    
    def _flash_linux_screen(self):
        """Linux画面フラッシュ（X11）"""
        try:
            import subprocess
            
            for _ in range(self.config.flash_count):
                # 画面の明度を一時的に変更
                subprocess.run(["xset", "dpms", "force", "off"], 
                             capture_output=True, timeout=1)
                time.sleep(self.config.flash_duration / 2)
                subprocess.run(["xset", "dpms", "force", "on"], 
                             capture_output=True, timeout=1)
                time.sleep(self.config.flash_duration / 2)
                
        except Exception as e:
            print(f"Linux flash error: {e}")
    
    def _flash_macos_screen(self):
        """macOS画面フラッシュ"""
        try:
            import subprocess
            
            for _ in range(self.config.flash_count):
                # AppleScriptを使用してフラッシュ効果
                script = '''
                tell application "System Events"
                    key down option
                    key up option
                end tell
                '''
                subprocess.run(["osascript", "-e", script], 
                             capture_output=True, timeout=2)
                time.sleep(self.config.flash_duration)
                
        except Exception as e:
            print(f"macOS flash error: {e}")
    
    def get_notification_history(self, limit: int = 10) -> list:
        """通知履歴を取得"""
        return self.notification_history[-limit:]
    
    def get_capabilities(self) -> Dict[str, bool]:
        """通知機能の対応状況を取得"""
        return {
            "toast": self.toast_available,
            "sound": self.sound_available,
            "flash": self.flash_available,
            "platform": self.platform
        }
    
    def test_notifications(self):
        """通知機能のテスト"""
        print(f"Testing notifications on {self.platform}...")
        
        capabilities = self.get_capabilities()
        print(f"Capabilities: {capabilities}")
        
        # 各レベルの通知をテスト
        test_cases = [
            (NotificationLevel.INFO, "情報", "これは情報通知のテストです"),
            (NotificationLevel.WARNING, "警告", "これは警告通知のテストです"),
            (NotificationLevel.URGENT, "緊急", "これは緊急通知のテストです")
        ]
        
        for level, title, message in test_cases:
            print(f"Testing {level.value} notification...")
            success = self.notify(title, message, level)
            print(f"Result: {'Success' if success else 'Failed'}")
            time.sleep(2)  # 通知間の間隔


# 便利関数とグローバルインスタンス
_default_service = None


def get_notification_service(config: Optional[NotificationConfig] = None) -> NotificationService:
    """デフォルトの通知サービスを取得"""
    global _default_service
    if _default_service is None:
        _default_service = NotificationService(config)
    return _default_service


def notify(title: str, 
           message: str, 
           level: NotificationLevel = NotificationLevel.INFO,
           **kwargs) -> bool:
    """便利関数：通知送信"""
    service = get_notification_service()
    return service.notify(title, message, level, **kwargs)


def notify_gentle_nudge(message: str) -> bool:
    """便利関数：軽い注意喚起"""
    return notify("Back2Task", message, NotificationLevel.WARNING)


def notify_strong_nudge(message: str) -> bool:
    """便利関数：強い注意喚起"""
    return notify("Back2Task - Focus!", message, NotificationLevel.URGENT, 
                  sound=True, flash=True)


def notify_task_complete(task_name: str) -> bool:
    """便利関数：タスク完了通知"""
    return notify("タスク完了", f"'{task_name}' が完了しました！", 
                  NotificationLevel.INFO, sound=True)


if __name__ == "__main__":
    # テスト実行
    service = NotificationService()
    service.test_notifications()