#!/usr/bin/env python3
"""
Face Detection App with YuNet + Streamlit
Cross-platform camera support (Ubuntu/Windows)
Bold, industrial aesthetic with real-time face detection
"""

import streamlit as st
import cv2
import numpy as np
from pathlib import Path
import time
from typing import Tuple, Optional

# Page config with bold industrial aesthetic
st.set_page_config(
    page_title="FACE DETECT // YUNET",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for industrial/brutalist aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Space+Grotesk:wght@400;600;700&display=swap');
    
    :root {
        --neon-cyan: #00F0FF;
        --neon-pink: #FF006E;
        --dark-bg: #0A0A0A;
        --darker-bg: #050505;
        --card-bg: #111111;
        --border-color: #333333;
        --text-primary: #FFFFFF;
        --text-secondary: #888888;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0A0A0A 0%, #1A1A1A 100%);
    }
    
    .main-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--text-primary);
        text-transform: uppercase;
        border-bottom: 3px solid var(--neon-cyan);
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        background: var(--card-bg);
        border: 1px solid var(--neon-cyan);
        color: var(--neon-cyan);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .status-active {
        background: var(--neon-cyan);
        color: var(--dark-bg);
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
    }
    
    .metric-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 3px solid var(--neon-pink);
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-left-width: 6px;
        transform: translateX(4px);
        box-shadow: 0 4px 20px rgba(255, 0, 110, 0.2);
    }
    
    .metric-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .video-container {
        position: relative;
        border: 2px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
        background: var(--darker-bg);
    }
    
    .video-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        border: 1px solid var(--neon-cyan);
        pointer-events: none;
        opacity: 0.3;
    }
    
    .stButton>button {
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--neon-cyan);
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0.75rem 2rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton>button:hover {
        background: var(--neon-cyan);
        color: var(--dark-bg);
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.4);
        transform: translateY(-2px);
    }
    
    .stButton>button[kind="primary"] {
        background: var(--neon-pink);
        border-color: var(--neon-pink);
        color: var(--text-primary);
    }
    
    .stButton>button[kind="primary"]:hover {
        background: #FF0080;
        box-shadow: 0 0 30px rgba(255, 0, 110, 0.4);
    }
    
    .sidebar-section {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .sidebar-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Scanline effect */
    .scanlines {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            rgba(0, 0, 0, 0.15),
            rgba(0, 0, 0, 0.15) 1px,
            transparent 1px,
            transparent 2px
        );
        pointer-events: none;
        z-index: 999;
        opacity: 0.3;
    }
</style>
""", unsafe_allow_html=True)

# Add scanline overlay
st.markdown('<div class="scanlines"></div>', unsafe_allow_html=True)


class YuNetDetector:
    """YuNet Face Detection with cross-platform support"""
    
    def __init__(self):
        self.detector = None
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
            st.info("⬇️ Downloading YuNet model (337KB)...")
            urllib.request.urlretrieve(url, model_path)
            st.success("✓ Model downloaded successfully")
            return True
        except Exception as e:
            st.error(f"✗ Failed to download model: {e}")
            st.markdown(f"[Download manually]({url})")
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
                score_threshold=0.9,
                nms_threshold=0.3,
                top_k=5000
            )
            return True
        except Exception as e:
            st.error(f"✗ Failed to initialize YuNet: {e}")
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
            
            for face in faces:
                x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                
                # Draw bounding box with neon aesthetic
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 240, 255), 2)
                
                # Add corner accents
                corner_length = 15
                cv2.line(frame, (x, y), (x + corner_length, y), (255, 0, 110), 3)
                cv2.line(frame, (x, y), (x, y + corner_length), (255, 0, 110), 3)
                cv2.line(frame, (x + w, y), (x + w - corner_length, y), (255, 0, 110), 3)
                cv2.line(frame, (x + w, y), (x + w, y + corner_length), (255, 0, 110), 3)
                cv2.line(frame, (x, y + h), (x + corner_length, y + h), (255, 0, 110), 3)
                cv2.line(frame, (x, y + h), (x, y + h - corner_length), (255, 0, 110), 3)
                cv2.line(frame, (x + w, y + h), (x + w - corner_length, y + h), (255, 0, 110), 3)
                cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_length), (255, 0, 110), 3)
                
                # Face label
                label = f"FACE #{face_count}"
                cv2.putText(frame, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 2)
        
        return frame, face_count


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


def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown('<div class="main-header">FACE DETECT // YUNET</div>', unsafe_allow_html=True)
    
    # Initialize detector
    if 'detector' not in st.session_state:
        st.session_state.detector = YuNetDetector()
        st.session_state.detector_initialized = st.session_state.detector.initialize()
    
    # Sidebar controls
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">⚙️ CONTROLS</div>', unsafe_allow_html=True)
        
        # Detection settings
        score_threshold = st.slider(
            "Score Threshold",
            min_value=0.1, max_value=0.99, value=0.9, step=0.05,
            help="Minimum confidence for face detection"
        )
        
        nms_threshold = st.slider(
            "NMS Threshold",
            min_value=0.1, max_value=0.99, value=0.3, step=0.05,
            help="Non-maximum suppression threshold"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # System status
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">📊 SYSTEM STATUS</div>', unsafe_allow_html=True)
        
        if st.session_state.detector_initialized:
            st.markdown('<span class="status-badge status-active">YUNET LOADED</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge">MODEL ERROR</span>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Info
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">ℹ️ INFO</div>', unsafe_allow_html=True)
        st.info("**YuNet** - Ultra-lightweight face detector\n\n• Size: 337KB\n• Speed: 49 FPS\n• Accuracy: 99.6%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 🎥 LIVE FEED")
        
        # Camera controls
        camera_container = st.container()
        
        with camera_container:
            if 'camera_active' not in st.session_state:
                st.session_state.camera_active = False
                st.session_state.cap = None
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("▶ START CAMERA", width='stretch'):
                    if not st.session_state.camera_active:
                        cap, backend_name = init_camera()
                        if cap:
                            st.session_state.cap = cap
                            st.session_state.camera_active = True
                            st.session_state.backend_name = backend_name
                            st.success(f"✓ Camera started ({backend_name})")
                            st.rerun()
                        else:
                            st.error("✗ Could not access camera")

            with col_btn2:
                if st.button("⏹ STOP CAMERA", width='stretch'):
                    if st.session_state.camera_active:
                        st.session_state.cap.release()
                        st.session_state.cap = None
                        st.session_state.camera_active = False
                        st.success("✓ Camera stopped")
                        st.rerun()
    
    # Camera feed
    if st.session_state.camera_active and st.session_state.cap:
        frame_placeholder = st.empty()
        
        # Metrics
        with col2:
            st.markdown("### 📈 METRICS")
            
            faces_container = st.container()
            fps_container = st.container()
            backend_container = st.container()
        
        # Frame processing loop
        while st.session_state.camera_active:
            ret, frame = st.session_state.cap.read()
            
            if not ret:
                st.error("✗ Failed to grab frame")
                break
            
            # Detect faces
            annotated_frame, face_count = st.session_state.detector.detect(frame)
            
            # Display frame
            frame_placeholder.image(annotated_frame, channels="BGR", use_container_width=True)
            
            # Update metrics
            with faces_container:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Faces Detected</div>
                    <div class="metric-value">{face_count}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with fps_container:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Processing</div>
                    <div class="metric-value">LIVE</div>
                </div>
                """, unsafe_allow_html=True)
            
            with backend_container:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Camera Backend</div>
                    <div class="metric-value" style="font-size: 1rem;">{st.session_state.get('backend_name', 'Unknown')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Small delay to prevent UI freezing
            time.sleep(0.01)
    
    else:
        # Placeholder when camera is off
        st.markdown("""
        <div style="text-align: center; padding: 4rem; background: #111; border: 2px dashed #333; border-radius: 8px;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📷</div>
            <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; color: #888;">
                CAMERA OFFLINE
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #666; margin-top: 1rem;">
                Press START CAMERA to begin face detection
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
