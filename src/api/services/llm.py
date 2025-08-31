import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

HTTP_OK = 200
IDLE_LONG_MS = 60_000
IDLE_SHORT_MS = 5_000


@dataclass
class NudgingPolicy:
    """Nudging policy response structure."""

    action: str  # "quiet", "gentle_nudge", "strong_nudge"
    reason: str
    tip: str | None = None
    confidence: float = 0.5


class LLMService:
    """OpenAI互換APIクライアント（LM Studio + Gemma 3 4B等に対応）."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout: float = 20.0,
    ) -> None:
        """初期化

        Args:
        base_url: OpenAI互換APIのベースURL（例: http://127.0.0.1:1234）
        model_name: 使用するモデル名（例: google/gemma-3-4b）
        timeout: APIタイムアウト(秒)

        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.chat_url = f"{self.base_url}/v1/chat/completions"

        # システムプロンプト
        self.system_prompt = """
You are a productivity nudging assistant.
Analyze the user's current activity and decide the best nudging action.

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
        self.last_call_time: float = 0.0
        self.min_call_interval = 1.0  # 最小呼び出し間隔（秒）

    def is_available(self) -> bool:
        """LLMサービスが利用可能かチェック."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
        except requests.RequestException:
            return False
        else:
            status_code: int = response.status_code
            return status_code == HTTP_OK

    def _rate_limit(self) -> None:
        """レート制限を適用."""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_call_interval:
            time.sleep(self.min_call_interval - elapsed)
        self.last_call_time = time.time()

    def _build_context_prompt(self, task: str, observations: dict[str, Any]) -> str:
        """観測データからコンテキストプロンプトを構築."""
        active_app = observations.get("active_app") or "unknown"
        title = observations.get("title") or ""
        url = observations.get("url") or ""
        idle_ms = observations.get("idle_ms", 0)
        screenshot = observations.get("screenshot") or ""

        # アイドル時間を分かりやすい形式に変換
        if idle_ms > IDLE_LONG_MS:
            idle_desc = (
                f"{idle_ms // IDLE_LONG_MS}min "
                f"{(idle_ms % IDLE_LONG_MS) // 1000}sec idle"
            )
        elif idle_ms > IDLE_SHORT_MS:
            idle_desc = f"{idle_ms // 1000}sec idle"
        else:
            idle_desc = "active"

        return f"""
Task: {task}
Current Activity:
- App: {active_app}
- Window: {title[:80]}
- URL: {url[:80] if url else "N/A"}
- Status: {idle_desc}
- Screenshot: {"Available" if screenshot else "Not available"}

Please analyze the screenshot (if available) to determine
if the user is focused on their task or being distracted.
Decide the best nudging action now.
""".strip()

    def decide_nudging_policy(
        self,
        task: str,
        observations: dict[str, Any],
    ) -> NudgingPolicy:
        """観測データに基づいてnudging policyを決定.

        Args:
            task: 現在のタスク名
            observations: 観測データ（active_app, title, url, idle_ms,
                ocr, phone_detected等）

        Returns:
            NudgingPolicy: 決定されたnudging policy

        """
        if not self.is_available():
            # LLM不可時は静的にquietを返す
            return NudgingPolicy(
                action="quiet",
                reason="LLM unavailable",
                tip=None,
                confidence=0.0,
            )

        try:
            # レート制限適用
            self._rate_limit()

            # プロンプト構築
            context_prompt = self._build_context_prompt(task, observations)

            # メッセージを構築（スクリーンショットが利用可能な場合は画像も含む）
            messages: list[dict[str, Any]] = [
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
                                    "url": f"data:image/png;base64,{screenshot}",
                                },
                            },
                        ],
                    },
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

            headers = {"Content-Type": "application/json"}

            response = requests.post(
                self.chat_url,
                json=payload,
                timeout=self.timeout,
                headers=headers,
            )

            if response.status_code != HTTP_OK:
                return NudgingPolicy(
                    action="quiet",
                    reason="LLM error",
                    tip=None,
                    confidence=0.0,
                )

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
                return NudgingPolicy(
                    action="quiet",
                    reason="LLM parse error",
                    tip=None,
                    confidence=0.0,
                )

        except requests.exceptions.Timeout:
            return NudgingPolicy(
                action="quiet",
                reason="LLM timeout",
                tip=None,
                confidence=0.0,
            )
        except requests.RequestException:
            return NudgingPolicy(
                action="quiet",
                reason="LLM exception",
                tip=None,
                confidence=0.0,
            )


# 便利関数
def create_llm_service(
    base_url: str | None = None,
    model_name: str | None = None,
) -> LLMService:
    """LLMサービスのファクトリ関数.

    環境変数で設定（必須）:
    - LLM_URL: OpenAI互換APIのベースURL（例: http://127.0.0.1:1234）
    - LLM_MODEL: 使用するモデル名（例: google/gemma-3-4b）
    """
    resolved_base = base_url or os.getenv("LLM_URL")
    resolved_model = model_name or os.getenv("LLM_MODEL")
    if not resolved_base or not resolved_model:
        msg = "LLM_URL and LLM_MODEL must be set (e.g., in .env.local)."
        raise RuntimeError(msg)
    return LLMService(base_url=resolved_base, model_name=resolved_model)
