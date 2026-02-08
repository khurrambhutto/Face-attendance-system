"""
YuNet Face Detector Module
Handles all face detection logic
"""

import cv2
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
    
    def process_video(self, video_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process video file for face detection
        
        Args:
            video_path: Path to video file
            progress_callback: Optional callback function(progress: float) for UI updates
            
        Returns:
            Dictionary with:
                - total_frames: Total frames processed
                - max_faces: Maximum faces in single frame
                - avg_faces: Average faces per frame
                - total_face_detections: Total face instances across all frames
                - top_frames: List of (frame_num, face_count, annotated_image) tuples (top 3)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Track all frames with their face counts
        frame_data = []
        face_counts = []
        
        frame_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect faces
            annotated_frame, face_count = self.detect(frame)
            
            # Store frame data
            frame_data.append({
                'frame_num': frame_num,
                'face_count': face_count,
                'annotated_image': annotated_frame.copy()
            })
            face_counts.append(face_count)
            
            # Update progress
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
                'top_frames': []
            }
        
        # Find top 3 frames with most faces
        sorted_frames = sorted(frame_data, key=lambda x: x['face_count'], reverse=True)[:3]
        
        # Prepare top frames data
        top_frames = []
        for frame_info in sorted_frames:
            # Convert BGR to RGB for Streamlit
            annotated_rgb = cv2.cvtColor(frame_info['annotated_image'], cv2.COLOR_BGR2RGB)
            top_frames.append({
                'frame_num': frame_info['frame_num'],
                'face_count': frame_info['face_count'],
                'image': annotated_rgb
            })
        
        return {
            'total_frames': total_frames,
            'max_faces': max(face_counts),
            'avg_faces': round(sum(face_counts) / len(face_counts), 2),
            'total_face_detections': sum(face_counts),
            'top_frames': top_frames
        }


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
