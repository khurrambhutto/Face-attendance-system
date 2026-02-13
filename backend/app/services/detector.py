import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Callable


class FaceDetector:
    def __init__(self, model_dir: str = "models"):
        self.detector = None
        self.recognizer = None
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def download_yunet_model(self) -> bool:
        model_path = self.model_dir / "face_detection_yunet_2023mar.onnx"

        if model_path.exists():
            return True

        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

        try:
            import urllib.request

            print(f"Downloading YuNet model from {url}...")
            urllib.request.urlretrieve(url, model_path)
            print("YuNet model downloaded successfully")
            return True
        except Exception as e:
            print(f"Failed to download YuNet model: {e}")
            return False

    def download_sface_model(self) -> bool:
        model_path = self.model_dir / "face_recognition_sface_2021dec.onnx"

        if model_path.exists():
            return True

        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

        try:
            import urllib.request

            print(f"Downloading SFace model from {url}...")
            urllib.request.urlretrieve(url, model_path)
            print("SFace model downloaded successfully")
            return True
        except Exception as e:
            print(f"Failed to download SFace model: {e}")
            return False

    def initialize(self, input_size: Tuple[int, int] = (640, 480)) -> bool:
        if not self.download_yunet_model():
            return False

        model_path = self.model_dir / "face_detection_yunet_2023mar.onnx"

        try:
            self.detector = cv2.FaceDetectorYN.create(
                str(model_path),
                "",
                input_size,
                score_threshold=0.8,
                nms_threshold=0.3,
                top_k=5000,
            )
            return True
        except Exception as e:
            print(f"Failed to initialize YuNet: {e}")
            return False

    def initialize_recognizer(self) -> bool:
        if not self.download_sface_model():
            return False

        model_path = self.model_dir / "face_recognition_sface_2021dec.onnx"

        try:
            self.recognizer = cv2.FaceRecognizerSF.create(str(model_path), "")
            return True
        except Exception as e:
            print(f"Failed to initialize SFace: {e}")
            return False

    def detect_faces(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        if self.detector is None:
            return None, 0

        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))

        _, faces = self.detector.detect(frame)

        if faces is None:
            return None, 0

        return faces, len(faces)

    def get_face_embedding(
        self, frame: np.ndarray, face_detection: np.ndarray
    ) -> Optional[np.ndarray]:
        if self.recognizer is None:
            if not self.initialize_recognizer():
                return None

        try:
            aligned_face = self.recognizer.alignCrop(frame, face_detection)
            embedding = self.recognizer.feature(aligned_face)
            return embedding
        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            return None

    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        e1 = np.array(embedding1).flatten()
        e2 = np.array(embedding2).flatten()

        dot_product = np.dot(e1, e2)
        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)

        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def check_face_quality(
        self, frame: np.ndarray, face: np.ndarray
    ) -> Tuple[bool, str]:
        x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])

        if w < 100 or h < 100:
            return False, "Move closer to the camera"

        frame_h, frame_w = frame.shape[:2]
        center_x = x + w // 2
        center_y = y + h // 2

        if not (frame_w * 0.25 < center_x < frame_w * 0.75):
            return False, "Center your face horizontally"
        if not (frame_h * 0.25 < center_y < frame_h * 0.75):
            return False, "Center your face vertically"

        return True, "Good face quality"

    def recognize_face(
        self,
        embedding: np.ndarray,
        enrolled_embeddings: List[Dict],
        threshold: float = 0.363,
    ) -> Tuple[Optional[str], Optional[str], float]:
        best_match = None
        best_name = None
        best_similarity = 0.0

        for student in enrolled_embeddings:
            student_id = student.get("id")
            student_name = student.get("student_name")
            embeddings_list = student.get("embeddings", [])

            for enrolled_emb in embeddings_list:
                similarity = self.cosine_similarity(embedding, enrolled_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = student_id
                    best_name = student_name

        if best_similarity >= threshold:
            return best_match, best_name, best_similarity

        return None, None, best_similarity

    def process_video(
        self,
        video_path: str,
        enrolled_students: List[Dict],
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Cannot open video"}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        recognized_students: Dict[str, Dict] = {}
        best_frames: Dict[str, Dict] = {}
        face_counts: List[int] = []
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            faces, face_count = self.detect_faces(frame)
            face_counts.append(face_count)

            if faces is not None and face_count > 0:
                for face in faces:
                    embedding = self.get_face_embedding(frame, face)
                    if embedding is not None:
                        student_id, student_name, similarity = self.recognize_face(
                            embedding, enrolled_students
                        )

                        if student_id:
                            if student_id not in recognized_students:
                                recognized_students[student_id] = {
                                    "student_name": student_name,
                                    "frames_detected": 0,
                                    "best_similarity": 0.0,
                                }

                            recognized_students[student_id]["frames_detected"] += 1

                            if (
                                similarity
                                > recognized_students[student_id]["best_similarity"]
                            ):
                                recognized_students[student_id]["best_similarity"] = (
                                    similarity
                                )

                                x, y, w, h = (
                                    int(face[0]),
                                    int(face[1]),
                                    int(face[2]),
                                    int(face[3]),
                                )
                                best_frame = frame.copy()
                                cv2.rectangle(
                                    best_frame, (x, y), (x + w, y + h), (0, 255, 0), 2
                                )
                                label = f"{student_name} ({similarity:.0%})"
                                cv2.putText(
                                    best_frame,
                                    label,
                                    (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (0, 255, 0),
                                    2,
                                )
                                best_frames[student_id] = {
                                    "frame_num": frame_num,
                                    "image": best_frame,
                                    "similarity": similarity,
                                }

            if progress_callback:
                progress_callback((frame_num + 1) / total_frames)

            frame_num += 1

        cap.release()

        return {
            "total_frames": total_frames,
            "frames_processed": frame_num,
            "fps": fps,
            "recognized_students": recognized_students,
            "best_frames": best_frames,
            "face_counts": face_counts,
        }

    def get_video_info(self, video_path: str) -> Optional[Dict]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        info = {
            "fps": int(cap.get(cv2.CAP_PROP_FPS)),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration": int(
                cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
            ),
        }

        cap.release()
        return info


detector = FaceDetector()


def get_detector() -> FaceDetector:
    return detector
