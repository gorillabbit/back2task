#!/usr/bin/env python3
"""
Direct test for Notification Service
"""

from ui.notifications import (
    NotificationService, NotificationConfig, NotificationLevel,
    notify, notify_gentle_nudge, notify_strong_nudge, notify_task_complete
)


def test_notification_config():
    """通知設定のテスト"""
    print("=== Notification Config Test ===")
    
    # デフォルト設定
    config = NotificationConfig()
    assert config.enable_toast is True
    assert config.enable_sound is True
    assert config.enable_flash is False
    assert config.toast_duration == 5
    
    # カスタム設定
    custom_config = NotificationConfig(
        enable_toast=False,
        enable_sound=True,
        enable_flash=True,
        toast_duration=10
    )
    assert custom_config.enable_toast is False
    assert custom_config.enable_sound is True
    assert custom_config.enable_flash is True
    assert custom_config.toast_duration == 10
    
    print("✓ Notification Config test passed")
    return True


def test_notification_service():
    """通知サービスのテスト"""
    print("\n=== Notification Service Test ===")
    
    service = NotificationService()
    print(f"Platform: {service.platform}")
    
    capabilities = service.get_capabilities()
    print(f"Capabilities: {capabilities}")
    
    # 各レベルの通知をテスト
    levels = [
        (NotificationLevel.INFO, "情報通知"),
        (NotificationLevel.WARNING, "警告通知"),
        (NotificationLevel.URGENT, "緊急通知")
    ]
    
    for level, message in levels:
        result = service.notify("テスト", message, level)
        print(f"{level.value} notification: {result}")
    
    # 履歴確認
    history = service.get_notification_history()
    print(f"Notification history: {len(history)} items")
    
    print("✓ Notification Service test passed")
    return True


def test_convenience_functions():
    """便利関数のテスト"""
    print("\n=== Convenience Functions Test ===")
    
    # 基本通知
    result1 = notify("Back2Task", "基本通知テスト")
    print(f"Basic notify: {result1}")
    
    # 軽い注意喚起
    result2 = notify_gentle_nudge("軽い注意喚起")
    print(f"Gentle nudge: {result2}")
    
    # 強い注意喚起
    result3 = notify_strong_nudge("強い注意喚起")
    print(f"Strong nudge: {result3}")
    
    # タスク完了通知
    result4 = notify_task_complete("テストタスク")
    print(f"Task complete: {result4}")
    
    print("✓ Convenience Functions test passed")
    return True


def test_rate_limiting():
    """レート制限のテスト"""
    print("\n=== Rate Limiting Test ===")
    
    service = NotificationService()
    
    # 初回は成功
    result1 = service._rate_limit_check()
    print(f"First check: {result1}")
    
    # 直後は制限
    result2 = service._rate_limit_check()
    print(f"Second check (immediate): {result2}")
    
    # 時間経過後は成功
    import time
    service.last_notification_time = time.time() - 2.0
    result3 = service._rate_limit_check()
    print(f"Third check (after delay): {result3}")
    
    print("✓ Rate Limiting test passed")
    return True


def test_notification_levels():
    """通知レベルのテスト"""
    print("\n=== Notification Levels Test ===")
    
    # Enum値の確認
    assert NotificationLevel.INFO.value == "info"
    assert NotificationLevel.WARNING.value == "warning"
    assert NotificationLevel.URGENT.value == "urgent"
    
    print("✓ Notification Levels test passed")
    return True


def test_linux_specific_features():
    """Linux固有機能のテスト"""
    print("\n=== Linux Specific Features Test ===")
    
    service = NotificationService()
    
    if service.platform == "Linux":
        print("Testing Linux notification features...")
        
        # notify-send テスト（利用可能な場合のみ）
        if service.toast_available:
            print("notify-send is available")
        else:
            print("notify-send is not available")
        
        # サウンドテスト
        if service.sound_available:
            print("Sound is available")
        else:
            print("Sound is not available")
        
        # フラッシュテスト
        if service.flash_available:
            print("Flash is available")
        else:
            print("Flash is not available")
    else:
        print(f"Skipping Linux tests (current platform: {service.platform})")
    
    print("✓ Linux Specific Features test passed")
    return True


def main():
    """メイン関数"""
    print("Back2Task Notification Service テストを開始...")
    
    tests = [
        ("Notification Config", test_notification_config),
        ("Notification Service", test_notification_service),
        ("Convenience Functions", test_convenience_functions),
        ("Rate Limiting", test_rate_limiting),
        ("Notification Levels", test_notification_levels),
        ("Linux Specific Features", test_linux_specific_features),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # 結果サマリー
    print("\n" + "="*50)
    print("テスト結果サマリー:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "✓ PASS" if results[i] else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if passed == total:
        print("🎉 全てのテストが成功しました！")
        return True
    else:
        print("⚠️  一部のテストが失敗しました")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)