import requests

from src.model.models import EventModel
from src.watchers.active_window import get_active_app
from src.watchers.idle import get_idle_ms
from src.watchers.logger import logger
from src.watchers.screen_capture import ScreenCapture

# HTTP status codes
HTTP_OK = 200


def collect_all_data() -> EventModel:
    """全てのWatcherからデータを収集."""
    window_data = get_active_app()
    screenshot_data = ScreenCapture().capture_as_base64()

    # データを統合
    return {
        "active_app": window_data.get("active_app") if window_data else None,
        "title": window_data.get("title", "") if window_data else "",
        "url": "",  # 将来的にブラウザURL取得を追加
        "idle_ms": get_idle_ms(),
        "screenshot": screenshot_data if screenshot_data else "",
        "ocr": None,
        "phone": None,
        "phone_detected": None,
    }


def send_event(event_data: EventModel) -> EventModel | None:
    """イベントデータをAPIに送信

    Args:
        event_data: 送信するイベントデータ

    Returns:
        bool: 送信成功時True

    """
    response = requests.post(
        "http://localhost:5577/events", json=event_data, timeout=20
    )

    status_code = int(getattr(response, "status_code", 0))
    ok = status_code == HTTP_OK
    logger.info(ok)
    response_json: EventModel = response.json()
    if ok:
        return response_json
    return None


def check_api_availability() -> bool:
    """APIの可用性をチェック."""
    # ステータスエンドポイントで確認
    response = requests.get("http://localhost:5577/status", timeout=3)
    status_code = int(getattr(response, "status_code", 0))
    return status_code == HTTP_OK


def main() -> None:
    """メイン関数."""
    api_status = check_api_availability()
    if api_status:
        while True:
            result = send_event(collect_all_data())
            logger.info(result)
            if result:
                logger.info("通知を送る")
                requests.post("http://localhost:5577/notify", json=result, timeout=3)


if __name__ == "__main__":
    main()
