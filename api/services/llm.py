import requests
import json
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class NudgingPolicy:
    """Nudging policy response structure"""

    action: str  # "quiet", "gentle_nudge", "strong_nudge"
    reason: str
    tip: Optional[str] = None
    confidence: float = 0.5


class LLMService:
    """OpenAI gpt-oss-20b を使用したLLMサービス"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model_name: str = "gpt-oss-20b",
        timeout: float = 20.0,
    ):
        """
        Args:
            base_url: vLLM APIサーバーのベースURL
            model_name: 使用するモデル名
            timeout: APIタイムアウト（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.chat_url = f"{self.base_url}/v1/chat/completions"

        # システムプロンプト
        self.system_prompt = """
You are a productivity nudging assistant. Analyze the user's current activity and decide the best nudging action.

Return ONLY a JSON object with these exact keys:
- action: one of "quiet", "gentle_nudge", "strong_nudge"
- reason: brief explanation (max 50 chars)
- tip: optional helpful suggestion (max 100 chars)

Rules:
- "quiet": User is being productive, no intervention needed
- "gentle_nudge": Minor distraction, gentle reminder
- "strong_nudge": Major distraction, needs immediate attention

Focus on being helpful, not annoying.
""".strip()

        # 最後のAPI呼び出し時刻（レート制限用）
        self.last_call_time = 0
        self.min_call_interval = 1.0  # 最小呼び出し間隔（秒）

    def is_available(self) -> bool:
        """LLMサービスが利用可能かチェック"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _rate_limit(self):
        """レート制限を適用"""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_call_interval:
            time.sleep(self.min_call_interval - elapsed)
        self.last_call_time = time.time()

    def _build_context_prompt(self, task: str, observations: Dict[str, Any]) -> str:
        """観測データからコンテキストプロンプトを構築"""
        active_app = observations.get("active_app") or "unknown"
        title = observations.get("title") or ""
        url = observations.get("url") or ""
        idle_ms = observations.get("idle_ms", 0)
        screenshot = observations.get("screenshot") or ""

        # アイドル時間を分かりやすい形式に変換
        if idle_ms > 60000:
            idle_desc = f"{idle_ms // 60000}min {(idle_ms % 60000) // 1000}sec idle"
        elif idle_ms > 5000:
            idle_desc = f"{idle_ms // 1000}sec idle"
        else:
            idle_desc = "active"

        context = f"""
Task: {task}
Current Activity:
- App: {active_app}
- Window: {title[:80]}
- URL: {url[:80] if url else "N/A"}
- Status: {idle_desc}
- Screenshot: {"Available" if screenshot else "Not available"}

Please analyze the screenshot (if available) to determine if the user is focused on their task or being distracted.
Decide the best nudging action now.
""".strip()

        return context

    def decide_nudging_policy(
        self, task: str, observations: Dict[str, Any]
    ) -> NudgingPolicy:
        """
        観測データに基づいてnudging policyを決定

        Args:
            task: 現在のタスク名
            observations: 観測データ（active_app, title, url, idle_ms, ocr, phone_detected等）

        Returns:
            NudgingPolicy: 決定されたnudging policy
        """
        if not self.is_available():
            # LLMが利用できない場合はルールベースフォールバック
            return self._fallback_policy(observations)

        try:
            # レート制限適用
            self._rate_limit()

            # プロンプト構築
            context_prompt = self._build_context_prompt(task, observations)

            # メッセージを構築（スクリーンショットが利用可能な場合は画像も含む）
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]

            screenshot = observations.get("screenshot")
            if screenshot:
                # ビジョン対応メッセージ
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": context_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot}"
                                },
                            },
                        ],
                    }
                )
            else:
                # テキストのみメッセージ
                messages.append({"role": "user", "content": context_prompt})

            # API呼び出し
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 150,
                "stop": ["\n\n", "```"],
            }

            response = requests.post(
                self.chat_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                print(f"LLM API エラー: HTTP {response.status_code}")
                return self._fallback_policy(observations)

            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].strip()

            # JSONパース
            try:
                policy_data = json.loads(content)
                return NudgingPolicy(
                    action=policy_data.get("action", "gentle_nudge"),
                    reason=policy_data.get("reason", "LLM decision"),
                    tip=policy_data.get("tip"),
                    confidence=0.8,
                )
            except json.JSONDecodeError:
                print(f"LLM JSON パースエラー: {content}")
                return self._fallback_policy(observations)

        except requests.exceptions.Timeout:
            print("LLM API タイムアウト")
            return self._fallback_policy(observations)
        except Exception as e:
            print(f"LLM API 予期しないエラー: {e}")
            return self._fallback_policy(observations)

    def _fallback_policy(self, observations: Dict[str, Any]) -> NudgingPolicy:
        """
        LLM が利用できない場合のルールベースフォールバック

        Args:
            observations: 観測データ

        Returns:
            NudgingPolicy: ルールベースで決定されたpolicy
        """
        active_app = observations.get("active_app", "")
        title = observations.get("title", "")
        url = observations.get("url", "")
        idle_ms = observations.get("idle_ms", 0)
        screenshot = observations.get("screenshot", "")

        # 強い脱線パターン
        strong_distractions = [
            "youtube",
            "tiktok",
            "twitter",
            "instagram",
            "facebook",
            "netflix",
            "prime video",
            "steam",
            "game",
        ]

        # 軽い脱線パターン
        gentle_distractions = ["reddit", "news", "shopping", "amazon", "ebay"]

        # 生産的パターン
        productive_patterns = [
            "code",
            "vscode",
            "vim",
            "emacs",
            "ide",
            "terminal",
            "documentation",
            "github",
            "stackoverflow",
            "programming",
        ]

        # 検出ロジック
        content_to_check = f"{active_app} {title} {url}"

        # 長時間アイドル -> 軽い脱線
        if idle_ms > 300000:  # 5分以上
            return NudgingPolicy(
                action="gentle_nudge",
                reason="Long idle time",
                tip="Ready to continue working?",
                confidence=0.7,
            )

        # スクリーンショットがある場合のルールベース判定はスキップ
        # （LLMによる判定が利用できない場合のみここに到達）
        if screenshot:
            return NudgingPolicy(
                action="quiet",
                reason="Screenshot analysis unavailable",
                tip=None,
                confidence=0.2,
            )

        # 強い脱線キーワード検出
        if any(keyword in content_to_check for keyword in strong_distractions):
            return NudgingPolicy(
                action="strong_nudge",
                reason="Distraction detected",
                tip="Get back to your task!",
                confidence=0.8,
            )

        # 軽い脱線キーワード検出
        if any(keyword in content_to_check for keyword in gentle_distractions):
            return NudgingPolicy(
                action="gentle_nudge",
                reason="Minor distraction",
                tip="Consider returning to work",
                confidence=0.6,
            )

        # 生産的パターン検出
        if any(keyword in content_to_check for keyword in productive_patterns):
            return NudgingPolicy(
                action="quiet", reason="Productive activity", tip=None, confidence=0.7
            )

        # デフォルト: 不明だが問題なし
        return NudgingPolicy(
            action="quiet", reason="Unknown activity", tip=None, confidence=0.3
        )

    def generate_task_suggestions(self, task_description: str) -> Dict[str, Any]:
        """
        タスク開始時の具体的な下位タスクや励ましメッセージを生成

        Args:
            task_description: タスクの説明

        Returns:
            Dict: 提案とメッセージ
        """
        if not self.is_available():
            return self._fallback_task_suggestions(task_description)

        try:
            self._rate_limit()

            system_prompt = """
You are a productivity assistant. Help break down tasks into actionable steps and provide encouragement.

Return a JSON object with:
- subtasks: array of 3-5 specific actionable steps
- encouragement: brief motivating message
- estimated_minutes: realistic time estimate per subtask

Keep responses concise and practical.
""".strip()

            user_prompt = f"Help me plan this task: {task_description}"

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            }

            response = requests.post(self.chat_url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"タスク提案生成エラー: {e}")

        return self._fallback_task_suggestions(task_description)

    def _fallback_task_suggestions(self, task_description: str) -> Dict[str, Any]:
        """タスク提案のフォールバック"""
        return {
            "subtasks": [
                "Start with planning and research",
                "Break down into smaller components",
                "Implement core functionality",
                "Test and validate results",
                "Review and finalize",
            ],
            "encouragement": "You can do this! Take it step by step.",
            "estimated_minutes": 10,
        }

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

        return {
            "object": "list",
            "data": [
                {
                    "id": self.model_name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "local",
                }
            ],
        }


# 便利関数
def create_llm_service(base_url: str = "http://localhost:8000") -> LLMService:
    """LLMサービスのファクトリ関数"""
    return LLMService(base_url=base_url)


def decide_nudging_policy(
    task: str, observations: Dict[str, Any], llm_service: Optional[LLMService] = None
) -> NudgingPolicy:
    """便利関数：nudging policy決定"""
    if llm_service is None:
        llm_service = create_llm_service()

    return llm_service.decide_nudging_policy(task, observations)
