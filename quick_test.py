#!/usr/bin/env python3
"""簡単なAPIテスト"""

import requests
import json
import time

def test_api():
    api_url = "http://127.0.0.1:5577"
    
    # 1. ステータス確認
    print("=== ステータステスト ===")
    try:
        response = requests.get(f"{api_url}/status")
        print(f"ステータス: {response.status_code}")
        if response.status_code == 200:
            status = response.json()
            print(f"レスポンス: {json.dumps(status, indent=2, ensure_ascii=False)}")
        else:
            print(f"エラー: {response.text}")
    except Exception as e:
        print(f"接続エラー: {e}")
        return False
    
    # 2. フォーカス開始
    print("\n=== フォーカス開始テスト ===")
    start_payload = {
        "task_id": "quick_test",
        "minutes": 1  # 1分のテスト
    }
    
    try:
        response = requests.post(f"{api_url}/focus/start", json=start_payload)
        print(f"フォーカス開始: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"エラー: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 3. イベント送信テスト
    print("\n=== イベント送信テスト ===")
    event_data = {
        "active_app": "python.exe",
        "title": "Back2Task テスト - ターミナル",
        "url": "",
        "idle_ms": 1000,
        "ocr": "Back2Task API test",
        "phone_detected": False,
        "phone": ""
    }
    
    try:
        response = requests.post(f"{api_url}/events", json=event_data)
        print(f"イベント送信: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"エラー: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 4. 再度ステータス確認
    print("\n=== 最終ステータス ===")
    try:
        response = requests.get(f"{api_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"レスポンス: {json.dumps(status, indent=2, ensure_ascii=False)}")
            
            # タスクの進捗を表示
            task = status.get("current_task", {})
            if task:
                progress = task.get("accum", 0) / task.get("goal", 1) * 100
                print(f"\n📊 タスク進捗: {progress:.1f}% ({task.get('accum', 0)}/{task.get('goal', 0)}秒)")
    except Exception as e:
        print(f"エラー: {e}")
    
    print("\n✅ APIテスト完了")
    return True

if __name__ == "__main__":
    test_api()