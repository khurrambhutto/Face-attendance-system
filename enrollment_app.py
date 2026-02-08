"""
Face Enrollment App with Streamlit GUI
Simple workflow: Start → Enter Info → Capture → Save
"""

import streamlit as st
import cv2
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from detector import YuNetDetector, init_camera


# Page config
st.set_page_config(
    page_title="Face Enrollment",
    page_icon="👤",
    layout="centered"
)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'start'
if 'enrollment_captures' not in st.session_state:
    st.session_state.enrollment_captures = []
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'detector' not in st.session_state:
    with st.spinner("Loading models..."):
        st.session_state.detector = YuNetDetector()
        st.session_state.detector_initialized = st.session_state.detector.initialize()
        st.session_state.sface_initialized = st.session_state.detector.initialize_sface()


# Create data directory structure
DATA_DIR = Path("data")
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
METADATA_DIR = DATA_DIR / "metadata"
PHOTOS_DIR = DATA_DIR / "photos"

for dir_path in [DATA_DIR, EMBEDDINGS_DIR, METADATA_DIR, PHOTOS_DIR]:
    dir_path.mkdir(exist_ok=True)


def load_embeddings():
    """Load embeddings from JSON file"""
    embeddings_file = EMBEDDINGS_DIR / "embeddings.json"
    if embeddings_file.exists():
        with open(embeddings_file, 'r') as f:
            return json.load(f)
    return {"students": {}}


def save_embeddings(data):
    """Save embeddings to JSON file"""
    embeddings_file = EMBEDDINGS_DIR / "embeddings.json"
    with open(embeddings_file, 'w') as f:
        json.dump(data, f, indent=2)


def check_face_quality(frame, face):
    """Check if face meets quality requirements"""
    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
    
    # Minimum size: 100x100
    if w < 100 or h < 100:
        return False, "Face too small - move closer"
    
    # Check centering
    frame_h, frame_w = frame.shape[:2]
    center_x = x + w // 2
    center_y = y + h // 2
    
    # Face should be in middle 50% of frame
    if not (frame_w * 0.25 < center_x < frame_w * 0.75):
        return False, "Move face to center horizontally"
    if not (frame_h * 0.25 < center_y < frame_h * 0.75):
        return False, "Move face to center vertically"
    
    return True, "Good quality"


def main():
    """Main Streamlit app - Simple linear workflow"""
    
    # STEP 1: START
    if st.session_state.step == 'start':
        st.title("👤 Face Enrollment System")
        st.write("\n")
        st.markdown("---")
        st.markdown("\n### Enroll a new student by capturing their face photos")
        st.markdown("### and generating SFace embeddings for recognition")
        st.markdown("\n---")
        
        st.write("\n")
        if st.button("▶️ START ENROLLMENT", type="primary", use_container_width=True):
            st.session_state.step = 'info'
            st.rerun()
    
    # STEP 2: ENTER STUDENT INFO
    elif st.session_state.step == 'info':
        st.title("👤 Face Enrollment System")
        st.markdown("---")
        
        st.subheader("Step 1/3: Student Information")
        
        col1, col2 = st.columns(2)
        with col1:
            student_id = st.text_input("Student ID *", key="input_id", placeholder="e.g., 101")
        with col2:
            student_name = st.text_input("Full Name *", key="input_name", placeholder="e.g., John Doe")
        
        st.markdown("---")
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.step = 'start'
                st.rerun()
        with col_right:
            if st.button("Next ➡️", type="primary", use_container_width=True):
                if student_id and student_name:
                    st.session_state.student_id = student_id
                    st.session_state.student_name = student_name
                    st.session_state.step = 'capture'
                    st.rerun()
                else:
                    st.error("Please enter both Student ID and Name")
    
    # STEP 3: CAPTURE PHOTOS
    elif st.session_state.step == 'capture':
        st.title("👤 Face Enrollment System")
        st.markdown("---")
        
        # Show student info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**ID:** {st.session_state.student_id}")
        with col2:
            st.info(f"**Name:** {st.session_state.student_name}")
        with col3:
            st.info(f"**Photos:** {len(st.session_state.enrollment_captures)}/3")
        
        st.markdown("---")
        
        # Start camera
        if not st.session_state.camera_active:
            if st.button("▶️ Start Camera", type="primary", use_container_width=True):
                cap, backend_name = init_camera()
                if cap:
                    st.session_state.cap = cap
                    st.session_state.camera_active = True
                    st.rerun()
                else:
                    st.error("✗ Could not access camera")
        else:
            col_capture, col_done = st.columns([2, 1])
            
            with col_capture:
                capture_btn = st.button("📸 Capture Photo", type="primary", use_container_width=True)
            
            with col_done:
                if len(st.session_state.enrollment_captures) >= 3:
                    if st.button("✅ Done - Save", type="primary", use_container_width=True):
                        st.session_state.step = 'save'
                        st.session_state.camera_active = False
                        if st.session_state.cap:
                            st.session_state.cap.release()
                            st.session_state.cap = None
                        st.rerun()
            
            st.markdown("---")
            
            # Camera feed
            frame_placeholder = st.empty()
            status_placeholder = st.empty()
            
            while st.session_state.camera_active:
                ret, frame = st.session_state.cap.read()
                if not ret:
                    break
                
                # Detect faces
                faces, num_faces = st.session_state.detector.detect_raw(frame)
                
                display_frame = frame.copy()
                
                if faces is not None and num_faces > 0:
                    face = faces[0]
                    is_good, message = check_face_quality(frame, face)
                    
                    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    color = (0, 255, 0) if is_good else (0, 0, 255)
                    
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(display_frame, message, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    status_placeholder.info(f"**Status:** {message}")
                else:
                    status_placeholder.warning("**Status:** No face detected")
                
                # Display frame
                frame_placeholder.image(display_frame, channels="BGR", use_container_width=True)
                
                # Handle capture
                if capture_btn and faces is not None and num_faces > 0:
                    face = faces[0]
                    is_good, _ = check_face_quality(frame, face)
                    
                    if is_good:
                        embedding = st.session_state.detector.get_face_embedding(frame, face)
                        
                        if embedding is not None:
                            st.session_state.enrollment_captures.append({
                                'embedding': embedding.tolist(),
                                'image': cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            st.success(f"✓ Photo {len(st.session_state.enrollment_captures)}/3 captured!")
                            st.rerun()
                        else:
                            st.error("✗ Failed to generate embedding")
                    else:
                        st.warning("✗ Face quality not good enough")
                
                import time
                time.sleep(0.01)
            
            # Show captured photos
            if st.session_state.enrollment_captures:
                st.markdown("---")
                st.subheader("🖼️ Captured Photos")
                cols = st.columns(len(st.session_state.enrollment_captures))
                for i, capture in enumerate(st.session_state.enrollment_captures):
                    with cols[i]:
                        st.image(capture['image'], caption=f"Photo {i+1}", use_container_width=True)
            
            # Back button
            st.markdown("---")
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.step = 'info'
                st.session_state.camera_active = False
                if st.session_state.cap:
                    st.session_state.cap.release()
                    st.session_state.cap = None
                st.rerun()
    
    # STEP 4: SAVE & CONFIRM
    elif st.session_state.step == 'save':
        st.title("👤 Face Enrollment System")
        st.markdown("---")
        
        st.subheader("Step 3/3: Save Enrollment")
        
        # Show summary
        st.markdown("### Student Information")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Student ID", st.session_state.student_id)
        with col2:
            st.metric("Name", st.session_state.student_name)
        
        st.metric("Photos Captured", len(st.session_state.enrollment_captures))
        
        st.markdown("---")
        
        # Show captured photos
        st.markdown("### Captured Photos")
        cols = st.columns(len(st.session_state.enrollment_captures))
        for i, capture in enumerate(st.session_state.enrollment_captures):
            with cols[i]:
                st.image(capture['image'], caption=f"Photo {i+1}", use_container_width=True)
        
        st.markdown("---")
        
        # Save button
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.step = 'capture'
                st.rerun()
        with col_right:
            if st.button("💾 Save Enrollment", type="primary", use_container_width=True):
                # Save embeddings
                embeddings_data = load_embeddings()
                embeddings_list = [capture['embedding'] for capture in st.session_state.enrollment_captures]
                
                embeddings_data["students"][st.session_state.student_id] = {
                    "name": st.session_state.student_name,
                    "embeddings": embeddings_list,
                    "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "num_embeddings": len(embeddings_list)
                }
                save_embeddings(embeddings_data)
                
                # Save metadata
                metadata_file = METADATA_DIR / "student_info.json"
                metadata_data = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata_data = json.load(f)
                
                metadata_data[st.session_state.student_id] = {
                    "name": st.session_state.student_name,
                    "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "num_photos": len(st.session_state.enrollment_captures)
                }
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata_data, f, indent=2)
                
                # Save photos
                student_photo_dir = PHOTOS_DIR / st.session_state.student_id
                student_photo_dir.mkdir(exist_ok=True)
                
                for i, capture in enumerate(st.session_state.enrollment_captures):
                    photo_path = student_photo_dir / f"photo_{i+1}.jpg"
                    img_bgr = cv2.cvtColor(capture['image'], cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(photo_path), img_bgr)
                
                # Clear and go to start
                st.session_state.enrollment_captures = []
                st.session_state.step = 'start'
                st.success(f"✓ Enrollment saved for {st.session_state.student_name}!")
                st.balloons()
                st.rerun()


if __name__ == "__main__":
    main()
