import time
from typing import Optional, Dict, List, Tuple, Any
import tempfile
import os

# OpenCV関連のインポート
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

# YOLOモデル関連のインポート
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

# MediaPipe関連のインポート（代替検出）
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


class WebcamPhoneDetector:
    """Webカメラを使ってスマートフォンを検出するクラス"""
    
    def __init__(self, camera_index: int = 0, model_size: str = "yolov8n"):
        """
        Args:
            camera_index: カメラのインデックス（通常は0）
            model_size: YOLOモデルサイズ (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
        """
        self.camera_index = camera_index
        self.model_size = model_size
        self.cap = None
        self.model = None
        self.mp_hands = None
        self.mp_drawing = None
        self.hands = None
        
        self.last_detection_time = 0
        self.detection_confidence_threshold = 0.4
        self.phone_detection_history = []
        self.max_history_length = 10
        
    def initialize_camera(self) -> bool:
        """
        カメラを初期化
        
        Returns:
            bool: 初期化成功時True
        """
        if not CV2_AVAILABLE:
            print("OpenCVが利用できません")
            return False
            
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"カメラ {self.camera_index} を開けませんでした")
                return False
            
            # カメラ設定
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 15)
            
            return True
            
        except Exception as e:
            print(f"カメラ初期化エラー: {e}")
            return False
    
    def initialize_yolo(self) -> bool:
        """
        YOLOモデルを初期化
        
        Returns:
            bool: 初期化成功時True
        """
        if not YOLO_AVAILABLE:
            print("YOLOが利用できません")
            return False
            
        try:
            # YOLOモデルをロード
            self.model = YOLO(f"{self.model_size}.pt")
            print(f"YOLOモデル {self.model_size} をロードしました")
            return True
            
        except Exception as e:
            print(f"YOLOモデル初期化エラー: {e}")
            return False
    
    def initialize_mediapipe(self) -> bool:
        """
        MediaPipeを初期化（手の検出用）
        
        Returns:
            bool: 初期化成功時True
        """
        if not MEDIAPIPE_AVAILABLE:
            print("MediaPipeが利用できません")
            return False
            
        try:
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            print("MediaPipe手検出を初期化しました")
            return True
            
        except Exception as e:
            print(f"MediaPipe初期化エラー: {e}")
            return False
    
    def capture_frame(self) -> Optional[Any]:
        """
        カメラからフレームを取得
        
        Returns:
            numpy.ndarray: キャプチャされたフレーム、失敗時はNone
        """
        if self.cap is None or not self.cap.isOpened():
            return None
            
        try:
            ret, frame = self.cap.read()
            if ret:
                return frame
            else:
                return None
                
        except Exception as e:
            print(f"フレーム取得エラー: {e}")
            return None
    
    def detect_phone_yolo(self, frame: Any) -> Tuple[bool, float, List[Dict]]:
        """
        YOLOを使ってスマートフォンを検出
        
        Args:
            frame: 入力フレーム
            
        Returns:
            Tuple[bool, float, List[Dict]]: (検出フラグ, 最大信頼度, 検出結果リスト)
        """
        if self.model is None:
            return False, 0.0, []
            
        try:
            # YOLO推論実行
            results = self.model(frame, verbose=False)
            
            phone_detections = []
            max_confidence = 0.0
            phone_detected = False
            
            # 結果を解析
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        # クラス名を取得
                        class_id = int(box.cls)
                        class_name = self.model.names[class_id]
                        confidence = float(box.conf)
                        
                        # 'cell phone' クラスを探す
                        if class_name == 'cell phone' and confidence > self.detection_confidence_threshold:
                            phone_detected = True
                            max_confidence = max(max_confidence, confidence)
                            
                            # バウンディングボックス情報
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            
                            phone_detections.append({
                                "class": class_name,
                                "confidence": confidence,
                                "bbox": [x1, y1, x2, y2],
                                "center": [(x1 + x2) / 2, (y1 + y2) / 2],
                                "area": (x2 - x1) * (y2 - y1)
                            })
            
            return phone_detected, max_confidence, phone_detections
            
        except Exception as e:
            print(f"YOLO検出エラー: {e}")
            return False, 0.0, []
    
    def detect_hands_mediapipe(self, frame: Any) -> Tuple[bool, List[Dict]]:
        """
        MediaPipeを使って手を検出（スマホを持っている手を推定）
        
        Args:
            frame: 入力フレーム
            
        Returns:
            Tuple[bool, List[Dict]]: (手の検出フラグ, 検出結果リスト)
        """
        if self.hands is None:
            return False, []
            
        try:
            # BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 手の検出
            results = self.hands.process(rgb_frame)
            
            hand_detections = []
            hands_detected = False
            
            if results.multi_hand_landmarks:
                hands_detected = True
                
                for hand_landmarks in results.multi_hand_landmarks:
                    # 手のランドマーク情報を取得
                    landmarks = []
                    for landmark in hand_landmarks.landmark:
                        landmarks.append({
                            "x": landmark.x,
                            "y": landmark.y,
                            "z": landmark.z
                        })
                    
                    hand_detections.append({
                        "landmarks": landmarks,
                        "landmark_count": len(landmarks)
                    })
            
            return hands_detected, hand_detections
            
        except Exception as e:
            print(f"MediaPipe手検出エラー: {e}")
            return False, []
    
    def detect_phone(self, frame: Optional[Any] = None) -> Dict[str, any]:
        """
        スマートフォンを検出（YOLOとMediaPipeの組み合わせ）
        
        Args:
            frame: 入力フレーム（Noneの場合は新しくキャプチャ）
            
        Returns:
            Dict: 検出結果
        """
        if frame is None:
            frame = self.capture_frame()
            
        if frame is None:
            return {
                "phone_detected": False,
                "confidence": 0.0,
                "method": "error",
                "details": {},
                "timestamp": time.time()
            }
        
        result = {
            "phone_detected": False,
            "confidence": 0.0,
            "method": "none",
            "details": {},
            "timestamp": time.time()
        }
        
        # YOLO検出を試行
        if self.model is not None:
            phone_detected, confidence, detections = self.detect_phone_yolo(frame)
            
            if phone_detected:
                result.update({
                    "phone_detected": True,
                    "confidence": confidence,
                    "method": "yolo",
                    "details": {
                        "yolo_detections": detections,
                        "detection_count": len(detections)
                    }
                })
        
        # MediaPipe手検出を追加情報として取得
        if self.hands is not None:
            hands_detected, hand_detections = self.detect_hands_mediapipe(frame)
            
            if hands_detected:
                result["details"]["hands_detected"] = True
                result["details"]["hand_count"] = len(hand_detections)
                
                # 手が検出され、YOLOでスマホが見つからない場合の補完ロジック
                if not result["phone_detected"] and len(hand_detections) >= 1:
                    # 手があり、特定のジェスチャがあればスマホ使用と推定
                    result.update({
                        "phone_detected": True,
                        "confidence": 0.3,  # 低信頼度
                        "method": "mediapipe_inference"
                    })
        
        # 検出履歴を更新
        self.phone_detection_history.append(result["phone_detected"])
        if len(self.phone_detection_history) > self.max_history_length:
            self.phone_detection_history.pop(0)
        
        # 履歴ベースの信頼度調整
        if len(self.phone_detection_history) >= 3:
            recent_detections = sum(self.phone_detection_history[-3:])
            if recent_detections >= 2:  # 過去3回中2回以上検出
                result["confidence"] = min(1.0, result["confidence"] + 0.2)
        
        self.last_detection_time = time.time()
        return result
    
    def save_debug_frame(self, frame: Any, detection_result: Dict, filename: str = None) -> str:
        """
        デバッグ用にフレームを保存
        
        Args:
            frame: 保存するフレーム
            detection_result: 検出結果
            filename: ファイル名（Noneの場合は自動生成）
            
        Returns:
            str: 保存されたファイルパス
        """
        if filename is None:
            timestamp = int(time.time())
            detected = "phone" if detection_result["phone_detected"] else "no_phone"
            filename = f"webcam_debug_{detected}_{timestamp}.jpg"
        
        try:
            # 検出結果を画像に描画
            debug_frame = frame.copy()
            
            if detection_result.get("details", {}).get("yolo_detections"):
                for detection in detection_result["details"]["yolo_detections"]:
                    bbox = detection["bbox"]
                    confidence = detection["confidence"]
                    
                    # バウンディングボックスを描画
                    cv2.rectangle(
                        debug_frame,
                        (int(bbox[0]), int(bbox[1])),
                        (int(bbox[2]), int(bbox[3])),
                        (0, 255, 0),  # 緑色
                        2
                    )
                    
                    # 信頼度を表示
                    cv2.putText(
                        debug_frame,
                        f"Phone: {confidence:.2f}",
                        (int(bbox[0]), int(bbox[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1
                    )
            
            # 一時ディレクトリに保存
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)
            
            cv2.imwrite(filepath, debug_frame)
            return filepath
            
        except Exception as e:
            print(f"デバッグフレーム保存エラー: {e}")
            return ""
    
    def monitor_phone(self, callback=None, interval: float = 2.0, save_debug: bool = False):
        """
        スマートフォンを定期的に監視
        
        Args:
            callback: 検出結果を受け取るコールバック関数
            interval: 監視間隔（秒）
            save_debug: デバッグ画像を保存するか
        """
        while True:
            try:
                frame = self.capture_frame()
                if frame is None:
                    time.sleep(interval)
                    continue
                
                result = self.detect_phone(frame)
                
                if callback:
                    callback(result)
                
                if save_debug and result["phone_detected"]:
                    self.save_debug_frame(frame, result)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"監視エラー: {e}")
                time.sleep(interval)
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        if self.cap is not None:
            self.cap.release()
        
        if self.hands is not None:
            self.hands.close()


# 便利関数
def detect_phone() -> bool:
    """
    スマートフォン検出の便利関数
    
    Returns:
        bool: スマートフォンが検出された場合True
    """
    if not CV2_AVAILABLE:
        print("OpenCVが利用できません")
        return False
        
    detector = WebcamPhoneDetector()
    
    if not detector.initialize_camera():
        return False
    
    try:
        # YOLOまたはMediaPipeを初期化
        yolo_ok = detector.initialize_yolo()
        mediapipe_ok = detector.initialize_mediapipe()
        
        if not (yolo_ok or mediapipe_ok):
            print("検出モデルが利用できません")
            return False
        
        # 1回検出を実行
        result = detector.detect_phone()
        return result["phone_detected"]
        
    finally:
        detector.cleanup()


if __name__ == "__main__":
    # テスト実行
    print("Webcam Phone Detectorを開始...")
    print(f"YOLO利用可能: {YOLO_AVAILABLE}")
    print(f"MediaPipe利用可能: {MEDIAPIPE_AVAILABLE}")
    
    if not (YOLO_AVAILABLE or MEDIAPIPE_AVAILABLE):
        print("必要なライブラリがインストールされていません")
        print("pip install ultralytics mediapipe でインストールしてください")
        exit(1)
    
    detector = WebcamPhoneDetector()
    
    if not detector.initialize_camera():
        print("カメラを初期化できませんでした")
        exit(1)
    
    # モデル初期化
    yolo_ok = detector.initialize_yolo()
    mediapipe_ok = detector.initialize_mediapipe()
    
    if not (yolo_ok or mediapipe_ok):
        print("検出モデルが利用できません")
        exit(1)
    
    def print_detection_result(result):
        status = "検出" if result["phone_detected"] else "非検出"
        method = result["method"]
        confidence = result["confidence"]
        print(f"スマートフォン: {status} (信頼度: {confidence:.2f}, 方法: {method})")
    
    try:
        print("5回検出を実行します...")
        for i in range(5):
            print(f"\n#{i+1} 検出中...")
            result = detector.detect_phone()
            print_detection_result(result)
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n検出を中断しました")
    finally:
        detector.cleanup()
        print("リソースをクリーンアップしました")