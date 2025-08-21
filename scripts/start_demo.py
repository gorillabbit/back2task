#!/usr/bin/env python3
"""
Back2Task Demo Launcher
MVPのデモンストレーション用スクリプト
"""

import subprocess
import time
import sys
import os
import requests
import threading
from pathlib import Path


class Back2TaskDemo:
    """Back2Task デモランチャー"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.venv_python = self.project_root / "venv" / "bin" / "python"
        if not self.venv_python.exists():
            # Windows環境
            self.venv_python = self.project_root / "venv" / "Scripts" / "python.exe"
        
        self.processes = []
        self.api_url = "http://localhost:5577"
        self.llm_url = "http://localhost:8000"
    
    def check_requirements(self) -> bool:
        """必要な環境をチェック"""
        print("🔍 環境チェック中...")
        
        # Python仮想環境
        if not self.venv_python.exists():
            print("❌ Python仮想環境が見つかりません")
            print("ヒント: python -m venv venv でセットアップしてください")
            return False
        print("✅ Python仮想環境: OK")
        
        # 必要なパッケージ
        try:
            result = subprocess.run([
                str(self.venv_python), "-c", 
                "import fastapi, uvicorn, requests, pydantic"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 必要なパッケージ: OK")
            else:
                print("❌ 必要なパッケージが不足しています")
                print("ヒント: pip install -r requirements.txt を実行してください")
                return False
        except Exception as e:
            print(f"❌ パッケージチェックエラー: {e}")
            return False
        
        # プロジェクトファイル
        required_files = [
            "api/main.py",
            "watchers/pump.py",
            "ui/notifications.py",
            "config/tasks.yaml"
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                print(f"❌ 必要なファイルが不足: {file_path}")
                return False
        print("✅ プロジェクトファイル: OK")
        
        return True
    
    def start_api_server(self) -> bool:
        """FastAPI サーバーを起動"""
        print("🚀 FastAPI サーバー起動中...")
        
        try:
            # uvicorn でFastAPIを起動
            process = subprocess.Popen([
                str(self.venv_python), "-m", "uvicorn",
                "api.main:app",
                "--reload",
                "--port", "5577",
                "--host", "127.0.0.1"
            ], cwd=self.project_root)
            
            self.processes.append(("FastAPI", process))
            
            # サーバー起動を待機
            for i in range(30):  # 30秒まで待機
                try:
                    response = requests.get(f"{self.api_url}/status", timeout=2)
                    if response.status_code == 200:
                        print("✅ FastAPI サーバー起動完了")
                        return True
                except:
                    pass
                time.sleep(1)
                print(f"   待機中... ({i+1}/30)")
            
            print("❌ FastAPI サーバー起動タイムアウト")
            return False
            
        except Exception as e:
            print(f"❌ FastAPI サーバー起動エラー: {e}")
            return False
    
    def check_llm_server(self) -> bool:
        """LLMサーバーの可用性をチェック"""
        print("🤖 LLMサーバーチェック中...")
        
        try:
            response = requests.get(f"{self.llm_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                model_ids = [m['id'] for m in models.get('data', [])]
                print(f"✅ LLMサーバー利用可能 (モデル: {model_ids})")
                return True
            else:
                print(f"⚠️  LLMサーバーエラー (HTTP {response.status_code})")
                return False
        except Exception as e:
            print(f"⚠️  LLMサーバーに接続できません: {e}")
            print("📝 LLMサーバー起動方法:")
            print("   python -m vllm.entrypoints.openai.api_server \\")
            print("     --model openai/gpt-oss-20b \\")
            print("     --port 8000")
            print("   (LLMサーバーなしでもルールベース判定で動作します)")
            return False
    
    def start_event_pump(self) -> bool:
        """Event Pump (Watchers) を起動"""
        print("👀 Event Pump (監視システム) 起動中...")
        
        try:
            process = subprocess.Popen([
                str(self.venv_python), "watchers/pump.py",
                "--api-url", f"{self.api_url}/events",
                "--interval", "3.0"  # デモ用に3秒間隔
            ], cwd=self.project_root)
            
            self.processes.append(("Event Pump", process))
            
            # 少し待ってプロセスが正常に起動したかチェック
            time.sleep(3)
            if process.poll() is None:
                print("✅ Event Pump 起動完了")
                return True
            else:
                print("❌ Event Pump 起動失敗")
                return False
                
        except Exception as e:
            print(f"❌ Event Pump 起動エラー: {e}")
            return False
    
    def demo_session(self):
        """デモセッション実行"""
        print("\n🎯 Back2Task デモセッション開始")
        print("="*50)
        
        # 1. タスク開始
        print("1️⃣ フォーカスタスクを開始...")
        start_payload = {
            "task_id": "demo_session",
            "minutes": 5  # 5分のデモセッション
        }
        
        try:
            response = requests.post(f"{self.api_url}/focus/start", json=start_payload)
            if response.status_code == 200:
                print("   ✅ デモタスク開始成功 (5分間)")
            else:
                print(f"   ❌ タスク開始失敗: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ タスク開始エラー: {e}")
            return
        
        # 2. 通知システムテスト
        print("\n2️⃣ 通知システムをテスト...")
        from ui.notifications import notify, NotificationLevel
        
        notify("Back2Task Demo", "デモセッションが開始されました", NotificationLevel.INFO)
        time.sleep(2)
        
        # 3. 模擬イベント送信
        print("\n3️⃣ 模擬作業イベントを送信...")
        
        demo_events = [
            {
                "description": "生産的な作業 (VSCode)",
                "event": {
                    "active_app": "Code.exe",
                    "title": "demo.py - Visual Studio Code",
                    "url": "",
                    "idle_ms": 1500,
                    "ocr": "def productivity_tracker():",
                    "phone_detected": False,
                    "phone": ""
                }
            },
            {
                "description": "軽い脱線 (技術記事)",
                "event": {
                    "active_app": "chrome.exe", 
                    "title": "Python Best Practices - Medium",
                    "url": "https://medium.com/python-tips",
                    "idle_ms": 2000,
                    "ocr": "python programming tips",
                    "phone_detected": False,
                    "phone": ""
                }
            },
            {
                "description": "重い脱線 (YouTube + スマホ)",
                "event": {
                    "active_app": "chrome.exe",
                    "title": "Funny Cat Videos - YouTube",
                    "url": "https://youtube.com/watch?v=cats",
                    "idle_ms": 1000,
                    "ocr": "funny cat compilation",
                    "phone_detected": True,
                    "phone": "jp.youtube"
                }
            }
        ]
        
        for i, demo_event in enumerate(demo_events):
            print(f"\n   📊 シナリオ {i+1}: {demo_event['description']}")
            
            try:
                response = requests.post(f"{self.api_url}/events", json=demo_event["event"])
                if response.status_code == 200:
                    result = response.json()
                    productive = result.get("productive", False)
                    print(f"      判定: {'✅ 生産的' if productive else '⚠️ 非生産的'}")
                    
                    # 非生産的な場合は通知
                    if not productive:
                        if "youtube" in demo_event["event"].get("title", "").lower():
                            notify("注意喚起", "YouTubeからタスクに戻りましょう！", NotificationLevel.URGENT)
                        else:
                            notify("軽い注意", "作業に集中しましょう", NotificationLevel.WARNING)
                else:
                    print(f"      ❌ イベント送信失敗: {response.status_code}")
            except Exception as e:
                print(f"      ❌ イベント送信エラー: {e}")
            
            time.sleep(5)  # デモ用の間隔
        
        # 4. セッション状態確認
        print("\n4️⃣ 現在のセッション状態...")
        try:
            response = requests.get(f"{self.api_url}/status")
            if response.status_code == 200:
                status = response.json()
                task = status.get("current_task", {})
                
                print(f"   タスクID: {task.get('id', 'なし')}")
                print(f"   目標時間: {task.get('goal', 0)}秒")
                print(f"   積算時間: {task.get('accum', 0)}秒")
                print(f"   進捗: {task.get('accum', 0)/task.get('goal', 1)*100:.1f}%")
                print(f"   現在の状態: {'生産的' if status.get('productive') else '非生産的'}")
                
                if status.get("done"):
                    print(f"   🎉 タスク完了: {status['done']}")
                    notify("タスク完了", "お疲れ様でした！", NotificationLevel.INFO)
            else:
                print(f"   ❌ ステータス取得失敗: {response.status_code}")
        except Exception as e:
            print(f"   ❌ ステータス取得エラー: {e}")
        
        print("\n🎉 デモセッション完了")
        print("💡 実際の使用では、以下のように操作します:")
        print("   1. タスクを開始: curl -X POST http://localhost:5577/focus/start -d '{\"task_id\":\"work\",\"minutes\":25}'")
        print("   2. Event Pump が自動的に作業を監視")
        print("   3. 脱線時には自動的に通知")
        print("   4. 目標時間達成で自動完了")
    
    def show_monitoring_info(self):
        """監視機能の説明を表示"""
        print("\n📊 監視機能について")
        print("="*50)
        print("Back2Task は以下の情報を監視します:")
        print()
        print("✅ 生産的な活動:")
        print("   • IDE・エディタ (VSCode, PyCharm, Vim等)")
        print("   • ターミナル・コマンドライン")
        print("   • 技術ドキュメント・Stack Overflow")
        print("   • GitHub・コードレビュー")
        print("   • 業務関連のWebサイト")
        print()
        print("⚠️ 注意が必要な活動:")
        print("   • SNS (Twitter, Instagram, Facebook等)")
        print("   • ニュースサイト (業務と無関係)")
        print("   • ショッピングサイト")
        print()
        print("🚨 非生産的な活動:")
        print("   • 動画サイト (YouTube, Netflix, TikTok等)")
        print("   • ゲーム (Steam, Epic Games等)")
        print("   • スマートフォン使用")
        print("   • 長時間のアイドル状態")
        print()
        print("🔒 プライバシー:")
        print("   • 全ての処理はローカルで実行")
        print("   • 画像・スクリーンショットは保存されません")
        print("   • 必要最小限の情報のみ処理")
    
    def cleanup(self):
        """プロセスのクリーンアップ"""
        print("\n🧹 プロセス終了中...")
        
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✅ {name} 終了")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"   ⚠️ {name} 強制終了")
            except Exception as e:
                print(f"   ❌ {name} 終了エラー: {e}")
    
    def run(self):
        """デモを実行"""
        print("🎯 Back2Task MVP Demo")
        print("="*50)
        
        try:
            # 1. 環境チェック
            if not self.check_requirements():
                print("\n❌ 環境チェック失敗。セットアップを完了してから再実行してください。")
                return
            
            # 2. LLMサーバーチェック（オプション）
            llm_available = self.check_llm_server()
            
            # 3. FastAPI起動
            if not self.start_api_server():
                print("\n❌ FastAPIサーバー起動失敗")
                return
            
            # 4. Event Pump起動
            if not self.start_event_pump():
                print("\n❌ Event Pump起動失敗")
                return
            
            # 5. 監視機能説明
            self.show_monitoring_info()
            
            # 6. デモ実行
            input("\n🚀 Enterキーを押してデモセッションを開始してください...")
            self.demo_session()
            
            # 7. 継続確認
            print("\n" + "="*50)
            print("🎮 デモが完了しました。")
            print("Back2Task は引き続き動作中です。")
            print("実際のタスクを開始するか、Ctrl+C で終了してください。")
            
            # 継続的な動作
            try:
                while True:
                    time.sleep(10)
                    # ステータス表示
                    try:
                        response = requests.get(f"{self.api_url}/status", timeout=2)
                        if response.status_code == 200:
                            status = response.json()
                            if status.get("current_task"):
                                task = status["current_task"]
                                progress = task.get("accum", 0) / task.get("goal", 1) * 100
                                print(f"📊 進捗: {progress:.1f}% ({task.get('accum', 0)}/{task.get('goal', 0)}秒)")
                    except:
                        pass
                        
            except KeyboardInterrupt:
                print("\n\n👋 Back2Task Demo を終了します...")
        
        finally:
            self.cleanup()


def main():
    """メイン関数"""
    demo = Back2TaskDemo()
    demo.run()


if __name__ == "__main__":
    main()