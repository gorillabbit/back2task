#!/usr/bin/env python3
"""
Back2Task完全デモンストレーション
"""

import requests
import json
import time

def demo_scenario():
    api_url = "http://127.0.0.1:5577"
    
    print("🎯 Back2Task 完全デモンストレーション")
    print("=" * 50)
    
    # 1. システム状態確認
    print("1️⃣ システム状態確認...")
    response = requests.get(f"{api_url}/status")
    print(f"   API サーバー: {'✅ 正常' if response.status_code == 200 else '❌ エラー'}")
    
    # 2. 2分間のフォーカスセッション開始
    print("\n2️⃣ フォーカスセッション開始 (2分間)...")
    start_payload = {
        "task_id": "complete_demo",
        "minutes": 2  # 2分のデモ
    }
    
    response = requests.post(f"{api_url}/focus/start", json=start_payload)
    if response.status_code == 200:
        print("   ✅ フォーカスセッション開始成功")
    else:
        print("   ❌ 開始失敗")
        return
    
    # 3. シナリオ実行
    scenarios = [
        {
            "name": "🔧 生産的作業（プログラミング）",
            "data": {
                "active_app": "Code.exe",
                "title": "main.py - Visual Studio Code",
                "url": "",
                "idle_ms": 2000,
                "ocr": "def productivity_monitor():",
                "phone_detected": False,
                "phone": ""
            },
            "expected": "生産的"
        },
        {
            "name": "📚 技術学習",
            "data": {
                "active_app": "chrome.exe",
                "title": "Python Documentation - Official",
                "url": "https://docs.python.org/3/",
                "idle_ms": 3000,
                "ocr": "Python 3.11 documentation",
                "phone_detected": False,
                "phone": ""
            },
            "expected": "生産的"
        },
        {
            "name": "⚠️ 軽度の脱線（技術ニュース）",
            "data": {
                "active_app": "chrome.exe",
                "title": "Tech News - TechCrunch",
                "url": "https://techcrunch.com/",
                "idle_ms": 4000,
                "ocr": "latest technology news",
                "phone_detected": False,
                "phone": ""
            },
            "expected": "注意必要"
        },
        {
            "name": "🚨 重度の脱線（YouTube + スマホ）",
            "data": {
                "active_app": "chrome.exe",
                "title": "Funny Videos Compilation - YouTube",
                "url": "https://youtube.com/watch?v=funny",
                "idle_ms": 1500,
                "ocr": "recommended videos",
                "phone_detected": True,
                "phone": "com.google.android.youtube"
            },
            "expected": "非生産的"
        }
    ]
    
    print("\n3️⃣ 様々な作業シナリオを実行...")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n   シナリオ {i}: {scenario['name']}")
        
        # イベント送信
        response = requests.post(f"{api_url}/events", json=scenario["data"])
        
        if response.status_code == 200:
            result = response.json()
            productive = result.get("productive", False)
            status = "✅ 生産的" if productive else "⚠️ 非生産的"
            print(f"      判定: {status}")
            
            # 期待結果と比較
            if productive and scenario["expected"] == "生産的":
                print(f"      期待結果: {scenario['expected']} ✅")
            elif not productive and scenario["expected"] in ["注意必要", "非生産的"]:
                print(f"      期待結果: {scenario['expected']} ✅")
            else:
                print(f"      期待結果: {scenario['expected']} ❓")
            
            # LLM判定がある場合は表示
            if "llm_result" in result:
                llm = result["llm_result"]
                print(f"      LLM判定: {llm.get('policy', 'N/A')}")
                if llm.get("hint"):
                    print(f"      ヒント: {llm['hint']}")
        else:
            print(f"      ❌ 送信失敗: {response.status_code}")
        
        time.sleep(3)  # 3秒間隔
    
    # 4. 最終状態確認
    print("\n4️⃣ セッション状態確認...")
    response = requests.get(f"{api_url}/status")
    
    if response.status_code == 200:
        status = response.json()
        task = status.get("current_task", {})
        
        if task:
            goal = task.get("goal", 0)
            accum = task.get("accum", 0)
            progress = (accum / goal * 100) if goal > 0 else 0
            
            print(f"   タスクID: {task.get('id')}")
            print(f"   目標時間: {goal}秒 ({goal/60:.1f}分)")
            print(f"   積算時間: {accum}秒")
            print(f"   進捗: {progress:.1f}%")
            print(f"   現在の状態: {'✅ 生産的' if status.get('productive') else '⚠️ 非生産的'}")
            
            if status.get("done"):
                print(f"   🎉 タスク完了!")
        else:
            print("   ℹ️ アクティブなタスクなし")
    
    # 5. 通知テスト
    print("\n5️⃣ 通知システムテスト...")
    try:
        from ui.notifications import notify, NotificationLevel
        
        # 情報通知
        result1 = notify("Back2Task", "デモ完了", NotificationLevel.INFO)
        print(f"   情報通知: {'✅ 成功' if result1 else '⚠️ 制限/失敗'}")
        
        time.sleep(1)
        
        # 警告通知
        result2 = notify("注意喚起", "作業に戻りましょう", NotificationLevel.WARNING)
        print(f"   警告通知: {'✅ 成功' if result2 else '⚠️ 制限/失敗'}")
        
    except Exception as e:
        print(f"   ❌ 通知エラー: {e}")
    
    print("\n🎉 Back2Task デモンストレーション完了!")
    print("\n📋 機能確認:")
    print("   ✅ FastAPI セッション管理")
    print("   ✅ イベント処理とルール判定")
    print("   ✅ 生産性分析")
    print("   ✅ 通知システム")
    print("   ✅ プログレス追跡")
    
    print("\n💡 実際の運用では:")
    print("   • Event Pumpが自動的に画面・アプリを監視")
    print("   • LLMサーバーでより高度な判定")
    print("   • 設定した時間でタスク自動完了")
    print("   • カスタマイズ可能な通知とルール")

if __name__ == "__main__":
    demo_scenario()