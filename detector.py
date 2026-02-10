"""
YuNet Face Detector Module
Handles all face detection and recognition logic
"""

import cv2
import json
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Callable


class YuNetDetector:
    """YuNet Face Detection with cross-platform support"""
    
    def __init__(self):
        self.detector = None
        self.recognizer = None  # SFace recognizer
        self.model_dir = Path("models")
        self.model_dir.mkdir(exist_ok=True)
        
    def download_model(self) -> bool:
        """Download YuNet model if not present"""
        model_path = self.model_dir / "face_detection_yunet_2023mar.onnx"
        
        if model_path.exists():
            return True
        
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        
        try:
            import urllib.request
            print(f"Downloading YuNet model from {url}...")
            urllib.request.urlretrieve(url, model_path)
            print("✓ Model downloaded successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to download model: {e}")
            return False
    
    def initialize(self, input_size: Tuple[int, int] = (640, 480)) -> bool:
        """Initialize YuNet detector"""
        if not self.download_model():
            return False
        
        model_path = self.model_dir / "face_detection_yunet_2023mar.onnx"
        
        try:
            self.detector = cv2.FaceDetectorYN.create(
                str(model_path),
                "", input_size,
                score_threshold=0.8, # change to 0.7 to increase detction 
                nms_threshold=0.3,
                top_k=5000
            )
            return True
        except Exception as e:
            print(f"✗ Failed to initialize YuNet: {e}")
            return False
    
    def download_sface_model(self) -> bool:
        """Download SFace model if not present"""
        model_path = self.model_dir / "face_recognition_sface_2021dec.onnx"
        
        if model_path.exists():
            return True
        
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
        
        try:
            import urllib.request
            print(f"Downloading SFace model from {url}...")
            urllib.request.urlretrieve(url, model_path)
            print("✓ SFace model downloaded successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to download SFace model: {e}")
            return False
    
    def initialize_sface(self) -> bool:
        """Initialize SFace recognizer"""
        if not self.download_sface_model():
            return False
        
        model_path = self.model_dir / "face_recognition_sface_2021dec.onnx"
        
        try:
            self.recognizer = cv2.FaceRecognizerSF.create(
                str(model_path),
                ""
            )
            return True
        except Exception as e:
            print(f"✗ Failed to initialize SFace: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, int]:
        """Detect faces in frame, return (annotated_frame, face_count)"""
        if self.detector is None:
            return frame, 0
        
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        
        _, faces = self.detector.detect(frame)
        
        face_count = 0
        if faces is not None:
            face_count = len(faces)
            
            for i, face in enumerate(faces):
                x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                
                # Draw simple green bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Face label
                label = f"Face {i+1}"
                cv2.putText(frame, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame, face_count
    
    def get_face_embedding(self, frame: np.ndarray, face_detection: np.ndarray) -> Optional[np.ndarray]:
        """Generate SFace embedding for a detected face
        
        Args:
            frame: Original image
            face_detection: Face detection array from YuNet
            
        Returns:
            128-dimensional embedding vector or None if failed
        """
        if self.recognizer is None:
            if not self.initialize_sface():
                return None
        
        try:
            # Align and crop face
            aligned_face = self.recognizer.alignCrop(frame, face_detection)
            
            # Generate 128D embedding
            embedding = self.recognizer.feature(aligned_face)
            
            return embedding
        except Exception as e:
            print(f"✗ Failed to generate embedding: {e}")
            return None
    
    def detect_raw(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """Detect faces without drawing, return (faces_array, face_count)
        
        Args:
            frame: Input image
            
        Returns:
            (faces_array, face_count) - Raw YuNet detections
        """
        if self.detector is None:
            return None, 0
        
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        
        _, faces = self.detector.detect(frame)
        
        if faces is None:
            return None, 0
        
        return faces, len(faces)
    
    def extract_frame_info(self, video_path: str) -> Dict:
        """Extract video metadata"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        info = {
            'fps': int(cap.get(cv2.CAP_PROP_FPS)),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
        }
        
        cap.release()
        return info
    
    def load_embeddings(self) -> Optional[Dict]:
        """Load enrolled student embeddings from disk"""
        embeddings_file = Path("data/embeddings/embeddings.json")
        
        if not embeddings_file.exists():
            return None
        
        with open(embeddings_file, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def cosine_similarity(embedding1, embedding2) -> float:
        """Calculate cosine similarity between two embeddings"""
        embedding1 = np.array(embedding1).flatten()
        embedding2 = np.array(embedding2).flatten()
        
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def recognize_face(self, embedding, embeddings_data, threshold=0.363):
        """
        Match a face embedding against enrolled students
        
        Returns:
            (student_id, student_name, similarity) or (None, None, 0)
        """
        best_match = None
        best_similarity = 0
        
        for student_id, student_data in embeddings_data["students"].items():
            for enrolled_embedding in student_data["embeddings"]:
                similarity = self.cosine_similarity(embedding, enrolled_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = student_id
        
        if best_similarity >= threshold:
            return best_match, embeddings_data["students"][best_match]["name"], best_similarity
        
        return None, None, best_similarity
    
    def detect_and_recognize(self, frame: np.ndarray, embeddings_data: Optional[Dict] = None) -> Tuple[np.ndarray, int, List[Dict]]:
        """
        Detect faces AND recognize them against enrolled students.
        
        Args:
            frame: Input image
            embeddings_data: Loaded embeddings dict (from load_embeddings)
            
        Returns:
            (annotated_frame, face_count, recognized_list)
            recognized_list contains dicts with keys: name, student_id, similarity
        """
        if self.detector is None:
            return frame, 0, []
        
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        
        _, faces = self.detector.detect(frame)
        
        face_count = 0
        recognized = []
        
        if faces is not None:
            face_count = len(faces)
            
            # Ensure SFace is initialized for recognition
            if embeddings_data and self.recognizer is None:
                self.initialize_sface()
            
            for face in faces:
                x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                
                label = "Unknown"
                color = (0, 0, 255)  # Red for unknown
                student_id = None
                similarity = 0.0
                
                # Try recognition if embeddings are available
                if embeddings_data and self.recognizer is not None:
                    embedding = self.get_face_embedding(frame, face)
                    if embedding is not None:
                        student_id, name, similarity = self.recognize_face(
                            embedding, embeddings_data
                        )
                        if student_id:
                            label = f"{name.strip()} ({similarity:.0%})"
                            color = (0, 255, 0)  # Green for recognized
                            recognized.append({
                                'name': name.strip(),
                                'student_id': student_id,
                                'similarity': similarity
                            })
                        else:
                            label = f"Unknown ({similarity:.0%})"
                
                # Draw bounding box and label
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label background for readability
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
                cv2.putText(frame, label, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame, face_count, recognized
    
    def process_video_with_recognition(self, video_path: str, embeddings_data: Optional[Dict] = None,
                                        progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process video with face detection AND recognition.
        
        Returns dict with:
            - total_frames, max_faces, avg_faces, total_face_detections
            - top_frames: top 3 frames with most faces (with name labels drawn)
            - recognized_students: set of all unique recognized student names
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_data = []
        face_counts = []
        all_recognized = {}  # student_id -> {name, best_similarity}
        
        frame_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect AND recognize faces
            annotated_frame, face_count, recognized = self.detect_and_recognize(frame, embeddings_data)
            
            # Track recognized students
            for r in recognized:
                sid = r['student_id']
                if sid not in all_recognized or r['similarity'] > all_recognized[sid]['similarity']:
                    all_recognized[sid] = {'name': r['name'], 'similarity': r['similarity']}
            
            frame_data.append({
                'frame_num': frame_num,
                'face_count': face_count,
                'annotated_image': annotated_frame.copy(),
                'recognized': recognized
            })
            face_counts.append(face_count)
            
            if progress_callback:
                progress = (frame_num + 1) / total_frames
                progress_callback(progress)
            
            frame_num += 1
        
        cap.release()
        
        if not face_counts:
            return {
                'total_frames': 0,
                'max_faces': 0,
                'avg_faces': 0.0,
                'total_face_detections': 0,
                'top_frames': [],
                'recognized_students': {}
            }
        
        # Find top 3 frames with most faces
        sorted_frames = sorted(frame_data, key=lambda x: x['face_count'], reverse=True)[:3]
        
        top_frames = []
        for frame_info in sorted_frames:
            annotated_rgb = cv2.cvtColor(frame_info['annotated_image'], cv2.COLOR_BGR2RGB)
            top_frames.append({
                'frame_num': frame_info['frame_num'],
                'face_count': frame_info['face_count'],
                'image': annotated_rgb,
                'recognized': frame_info['recognized']
            })
        
        return {
            'total_frames': total_frames,
            'max_faces': max(face_counts),
            'avg_faces': round(sum(face_counts) / len(face_counts), 2),
            'total_face_detections': sum(face_counts),
            'top_frames': top_frames,
            'recognized_students': all_recognized
        }

    def process_video(self, video_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process video file for face detection only (no recognition).
        Kept for backward compatibility.
        """
        return self.process_video_with_recognition(video_path, None, progress_callback)


def init_camera():
    """Initialize camera with cross-platform backend support"""
    backends = [
        (cv2.CAP_ANY, "Auto"),
        (cv2.CAP_DSHOW, "DirectShow (Windows)"),
        (cv2.CAP_V4L2, "V4L2 (Linux)"),
    ]
    
    for backend_id, backend_name in backends:
        cap = cv2.VideoCapture(0, backend_id)
        if cap.isOpened():
            return cap, backend_name
    
    return None, None
