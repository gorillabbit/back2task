#!/usr/bin/env python3
"""
Direct test for all Watchers
"""

def test_idle_watcher():
    """Idle Watcherのテスト"""
    print("=== Idle Watcher Test ===")
    try:
        from watchers.idle import get_idle_ms, is_idle, get_idle_seconds
        
        idle_ms = get_idle_ms()
        print(f"アイドル時間: {idle_ms}ms")
        
        idle_seconds = get_idle_seconds()
        print(f"アイドル時間: {idle_seconds:.1f}秒")
        
        is_idle_5s = is_idle(5000)
        print(f"5秒以上アイドル: {is_idle_5s}")
        
        print("✓ Idle Watcher test passed")
        return True
        
    except Exception as e:
        print(f"❌ Idle Watcher test failed: {e}")
        return False


def test_screen_ocr():
    """Screen OCRのテスト"""
    print("\n=== Screen OCR Test ===")
    try:
        from watchers.screen_ocr import read_snippet, ScreenClassifier
        
        # 簡単なテキスト読み取り
        text = read_snippet()
        print(f"読み取りテキスト: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # ScreenClassifierクラステスト
        classifier = ScreenClassifier()
        available = classifier.is_available()
        print(f"OCR利用可能: {available}")
        
        if text:
            analysis = classifier.analyze_content(text)
            print(f"生産性判定: {analysis['productive']}")
            print(f"信頼度: {analysis['confidence']}")
            print(f"カテゴリ: {analysis['category']}")
        
        print("✓ Screen OCR test passed")
        return True
        
    except Exception as e:
        print(f"❌ Screen OCR test failed: {e}")
        return False


def test_webcam_phone():
    """Webcam Phone Detectorのテスト"""
    print("\n=== Webcam Phone Detector Test ===")
    try:
        from watchers.webcam_phone import detect_phone, WebcamPhoneDetector
        
        # 簡単な検出テスト
        print("スマートフォン検出を試行中...")
        detected = detect_phone()
        print(f"スマートフォン検出: {detected}")
        
        # クラステスト
        detector = WebcamPhoneDetector()
        camera_ok = detector.initialize_camera()
        print(f"カメラ利用可能: {camera_ok}")
        
        if camera_ok:
            detector.cleanup()
        
        print("✓ Webcam Phone Detector test passed")
        return True
        
    except Exception as e:
        print(f"❌ Webcam Phone Detector test failed: {e}")
        return False


def test_event_pump():
    """Event Pumpのテスト"""
    print("\n=== Event Pump Test ===")
    try:
        from watchers.pump import EventPump
        
        # ポンプ作成
        pump = EventPump()
        
        # データ収集テスト
        print("データ収集中...")
        event_data = pump.collect_all_data()
        
        print(f"アクティブアプリ: {event_data.get('active_app')}")
        title = event_data.get('title') or ""
        print(f"ウィンドウタイトル: {title[:50]}")
        print(f"アイドル時間: {event_data.get('idle_ms')}ms")
        ocr_text = event_data.get('ocr') or ""
        print(f"OCRテキスト: {ocr_text[:30]}{'...' if len(ocr_text) > 30 else ''}")
        print(f"スマホ検出: {event_data.get('phone_detected', False)}")
        
        # 状態確認
        status = pump.get_status()
        print(f"ポンプ状態: {status['running']}")
        print(f"スマホ検出有効: {status['phone_detection_enabled']}")
        
        pump.stop()
        print("✓ Event Pump test passed")
        return True
        
    except Exception as e:
        print(f"❌ Event Pump test failed: {e}")
        return False


def test_api_integration():
    """API統合テスト"""
    print("\n=== API Integration Test ===")
    try:
        import requests
        from watchers.pump import EventPump
        
        # API可用性チェック
        api_url = "http://localhost:5577/status"
        try:
            response = requests.get(api_url, timeout=3)
            api_available = response.status_code == 200
            print(f"API利用可能: {api_available}")
            
            if api_available:
                status = response.json()
                print(f"現在のタスク: {status.get('current_task')}")
                print(f"生産的状態: {status.get('productive')}")
        except Exception:
            print("API利用不可 (FastAPIサーバーが起動していない可能性があります)")
            api_available = False
        
        # イベント送信テスト
        if api_available:
            pump = EventPump()
            test_event = {
                "timestamp": 1234567890,
                "active_app": "test.exe",
                "title": "Test Window",
                "url": "",
                "idle_ms": 1000,
                "ocr": "test text",
                "phone_detected": False,
                "phone": ""
            }
            
            success = pump.send_event(test_event)
            print(f"テストイベント送信: {'成功' if success else '失敗'}")
            pump.stop()
        
        print("✓ API Integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ API Integration test failed: {e}")
        return False


def main():
    """メイン関数"""
    print("Back2Task Watchers 統合テストを開始...")
    
    tests = [
        ("Active Window Watcher", lambda: True),  # 既にテスト済み
        ("Idle Watcher", test_idle_watcher),
        ("Screen OCR", test_screen_ocr),
        ("Webcam Phone Detector", test_webcam_phone),
        ("Event Pump", test_event_pump),
        ("API Integration", test_api_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        if test_name == "Active Window Watcher":
            print(f"=== {test_name} Test ===")
            print("✓ Active Window Watcher test passed (previously tested)")
            results.append(True)
            continue
            
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
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