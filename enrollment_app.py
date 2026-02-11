"""
Face Enrollment App with Streamlit GUI
Simple workflow: Start → Enter Info → Capture → Save
"""

import streamlit as st
import cv2
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from supabase import create_client
from detector import YuNetDetector


# Page config
st.set_page_config(
    page_title="Quick Face Enroll",
    page_icon="👤",
    layout="centered"
)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'start'
if 'enrollment_captures' not in st.session_state:
    st.session_state.enrollment_captures = []
if 'camera_input_counter' not in st.session_state:
    st.session_state.camera_input_counter = 0
if 'last_photo_signature' not in st.session_state:
    st.session_state.last_photo_signature = None
if 'detector' not in st.session_state:
    with st.spinner("Getting things ready..."):
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


def get_supabase_client(show_error=False):
    """Create Supabase client from Streamlit secrets."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        if show_error:
            st.error("Supabase secrets missing. Add SUPABASE_URL and SUPABASE_KEY in Streamlit settings.")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        if show_error:
            st.error(f"Could not connect to Supabase: {e}")
        return None


def get_public_url(storage_bucket, file_path):
    """Get a public URL and gracefully handle SDK return shape differences."""
    public_url = storage_bucket.get_public_url(file_path)
    if isinstance(public_url, str):
        return public_url
    if isinstance(public_url, dict):
        return (
            public_url.get("publicUrl")
            or public_url.get("publicURL")
            or public_url.get("signedURL")
            or file_path
        )
    return file_path


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


def load_metadata():
    """Load student metadata from JSON file"""
    metadata_file = METADATA_DIR / "student_info.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return {}


def normalize_name(value):
    """Normalize names for case-insensitive duplicate checks."""
    return " ".join(value.strip().lower().split())


def build_unique_record_key(existing_data, base_key):
    """Create a unique key when the same ID is enrolled multiple times."""
    if base_key not in existing_data:
        return base_key

    counter = 2
    while True:
        candidate = f"{base_key}__{counter}"
        if candidate not in existing_data:
            return candidate
        counter += 1


def check_face_quality(frame, face):
    """Check if face meets quality requirements"""
    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
    
    # Minimum size: 100x100
    if w < 100 or h < 100:
        return False, "Move a little closer"
    
    # Check centering
    frame_h, frame_w = frame.shape[:2]
    center_x = x + w // 2
    center_y = y + h // 2
    
    # Face should be in middle 50% of frame
    if not (frame_w * 0.25 < center_x < frame_w * 0.75):
        return False, "Center your face in the frame"
    if not (frame_h * 0.25 < center_y < frame_h * 0.75):
        return False, "Center your face in the frame"
    
    return True, "Great, hold still"


def apply_minimal_ui():
    """Simple visual style for a cleaner, consumer-facing app."""
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                max-width: 760px;
            }
            .small-note {
                color: #6b7280;
                font-size: 0.95rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    """Main Streamlit app - Simple linear workflow"""
    apply_minimal_ui()

    # STEP 1: START
    if st.session_state.step == 'start':
        st.title("👤 Quick Face Enroll")
        st.caption("A fast, simple 3-step flow")
        st.markdown("---")
        st.markdown("### Ready to enroll?")
        st.markdown(
            "<p class='small-note'>You will add your basic info and take 3 photos.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if st.button("Start", type="primary", use_container_width=True):
            st.session_state.step = 'info'
            st.rerun()
    
    # STEP 2: ENTER STUDENT INFO
    elif st.session_state.step == 'info':
        st.title("👤 Quick Face Enroll")
        st.markdown("---")
        st.subheader("Step 1 of 3")
        st.caption("Enter your details")

        col1, col2 = st.columns(2)
        with col1:
            student_id = st.text_input("Your ID", key="input_id", placeholder="e.g., 101")
        with col2:
            student_name = st.text_input("Your Name", key="input_name", placeholder="e.g., John Doe")
        
        st.markdown("---")
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("Back", use_container_width=True):
                st.session_state.step = 'start'
                st.rerun()
        with col_right:
            if st.button("Next", type="primary", use_container_width=True):
                normalized_id = student_id.strip()
                normalized_name = " ".join(student_name.strip().split())

                if normalized_id and normalized_name:
                    embeddings_data = load_embeddings()
                    metadata_data = load_metadata()
                    supabase = get_supabase_client(show_error=False)
                    supabase_table = st.secrets.get("SUPABASE_TABLE", "enrollments")

                    existing_names = set()
                    for student in embeddings_data.get("students", {}).values():
                        if isinstance(student, dict) and student.get("name"):
                            existing_names.add(normalize_name(student["name"]))
                    for student in metadata_data.values():
                        if isinstance(student, dict) and student.get("name"):
                            existing_names.add(normalize_name(student["name"]))

                    # Also check names already saved online in Supabase.
                    if supabase:
                        try:
                            response = supabase.table(supabase_table).select("name").execute()
                            for row in (response.data or []):
                                name_value = row.get("name")
                                if name_value:
                                    existing_names.add(normalize_name(name_value))
                        except Exception:
                            # Keep app usable even if online read fails.
                            pass

                    if normalize_name(normalized_name) in existing_names:
                        st.error("This name is already enrolled. You cannot enroll the same name twice.")
                    else:
                        st.session_state.student_id = normalized_id
                        st.session_state.student_name = normalized_name
                        st.session_state.last_photo_signature = None
                        st.session_state.step = 'capture'
                        st.rerun()
                else:
                    st.error("Please fill in both fields.")
    
    # STEP 3: CAPTURE PHOTOS
    elif st.session_state.step == 'capture':
        st.title("👤 Quick Face Enroll")
        st.markdown("---")
        st.subheader("Step 2 of 3")
        st.caption("Take 3 clear photos")
        
        # Show student info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"ID: {st.session_state.student_id}")
        with col2:
            st.info(f"Name: {st.session_state.student_name}")
        with col3:
            st.info(f"Photos: {len(st.session_state.enrollment_captures)}/3")
        
        st.markdown("---")
        st.caption("Tap Capture once. Good photos are added automatically.")

        camera_file = st.camera_input(
            "Take a photo",
            key=f"camera_photo_{st.session_state.camera_input_counter}"
        )

        if camera_file is not None:
            raw_photo = camera_file.getvalue()
            photo_signature = hashlib.sha1(raw_photo).hexdigest()
            file_bytes = np.frombuffer(raw_photo, dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if frame is None:
                st.error("Could not read photo. Please retake.")
            else:
                faces, num_faces = st.session_state.detector.detect_raw(frame)
                display_frame = frame.copy()
                is_good = False

                if faces is not None and num_faces > 0:
                    face = faces[0]
                    is_good, message = check_face_quality(frame, face)
                    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    color = (0, 255, 0) if is_good else (0, 0, 255)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(display_frame, message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    st.info(message)
                else:
                    st.warning("No face found. Please retake.")

                st.image(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB), use_container_width=True)

                # Auto-save each newly captured valid photo (no extra Add button).
                is_new_photo = st.session_state.last_photo_signature != photo_signature
                if is_good and is_new_photo:
                    embedding = st.session_state.detector.get_face_embedding(frame, faces[0])
                    if embedding is None:
                        st.error("Could not save this photo. Please retake.")
                    else:
                        st.session_state.enrollment_captures.append({
                            'embedding': embedding.tolist(),
                            'image': cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.session_state.last_photo_signature = photo_signature
                        st.session_state.camera_input_counter += 1
                        st.success(f"Photo {len(st.session_state.enrollment_captures)}/3 captured.")
                        st.rerun()

        # Show captured photos
        if st.session_state.enrollment_captures:
            st.markdown("---")
            st.subheader("Your Photos")
            cols = st.columns(len(st.session_state.enrollment_captures))
            for i, capture in enumerate(st.session_state.enrollment_captures):
                with cols[i]:
                    st.image(capture['image'], caption=f"Photo {i+1}", use_container_width=True)

        st.markdown("---")
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("Back", use_container_width=True):
                st.session_state.last_photo_signature = None
                st.session_state.step = 'info'
                st.rerun()
        with col_right:
            if len(st.session_state.enrollment_captures) >= 3:
                if st.button("Continue", type="primary", use_container_width=True):
                    st.session_state.step = 'save'
                    st.rerun()
    
    # STEP 4: SAVE & CONFIRM
    elif st.session_state.step == 'save':
        st.title("👤 Quick Face Enroll")
        st.markdown("---")
        st.subheader("Step 3 of 3")
        st.caption("Review and save")
        
        # Show summary
        st.markdown("### Your Details")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ID", st.session_state.student_id)
        with col2:
            st.metric("Name", st.session_state.student_name)
        
        st.metric("Photos", len(st.session_state.enrollment_captures))
        
        st.markdown("---")
        
        # Show captured photos
        st.markdown("### Photos")
        cols = st.columns(len(st.session_state.enrollment_captures))
        for i, capture in enumerate(st.session_state.enrollment_captures):
            with cols[i]:
                st.image(capture['image'], caption=f"Photo {i+1}", use_container_width=True)
        
        st.markdown("---")
        
        # Save button
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("Back", use_container_width=True):
                st.session_state.step = 'capture'
                st.rerun()
        with col_right:
            if st.button("Save", type="primary", use_container_width=True):
                supabase = get_supabase_client(show_error=True)
                if not supabase:
                    return

                supabase_bucket_name = st.secrets.get("SUPABASE_BUCKET", "enrollment-photos")
                supabase_table = st.secrets.get("SUPABASE_TABLE", "enrollments")
                storage_bucket = supabase.storage.from_(supabase_bucket_name)
                enrollment_uuid = str(uuid4())

                embeddings_list = [capture['embedding'] for capture in st.session_state.enrollment_captures]
                photo_urls = []

                # Upload photos to Supabase Storage and collect URLs.
                try:
                    for i, capture in enumerate(st.session_state.enrollment_captures):
                        img_bgr = cv2.cvtColor(capture['image'], cv2.COLOR_RGB2BGR)
                        success, encoded_image = cv2.imencode(".jpg", img_bgr)
                        if not success:
                            raise ValueError("Image encoding failed")

                        photo_path = (
                            f"{st.session_state.student_id}/{enrollment_uuid}/photo_{i+1}.jpg"
                        )
                        storage_bucket.upload(
                            path=photo_path,
                            file=encoded_image.tobytes(),
                            file_options={"content-type": "image/jpeg"},
                        )
                        photo_urls.append(get_public_url(storage_bucket, photo_path))

                    payload = {
                        "student_id": st.session_state.student_id,
                        "name": st.session_state.student_name,
                        "photo_urls": photo_urls,
                        "embeddings": embeddings_list,
                    }
                    supabase.table(supabase_table).insert(payload).execute()
                except Exception as e:
                    st.error(f"Could not save enrollment online: {e}")
                    st.info("Please check bucket/table names and Supabase key permissions.")
                    return

                # Save embeddings
                embeddings_data = load_embeddings()
                record_id = build_unique_record_key(
                    embeddings_data["students"], st.session_state.student_id
                )

                embeddings_data["students"][record_id] = {
                    "student_id": st.session_state.student_id,
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

                metadata_record_id = build_unique_record_key(metadata_data, st.session_state.student_id)
                metadata_data[metadata_record_id] = {
                    "student_id": st.session_state.student_id,
                    "name": st.session_state.student_name,
                    "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "num_photos": len(st.session_state.enrollment_captures)
                }
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata_data, f, indent=2)
                
                # Save photos
                student_photo_dir = PHOTOS_DIR / record_id
                student_photo_dir.mkdir(exist_ok=True)
                
                for i, capture in enumerate(st.session_state.enrollment_captures):
                    photo_path = student_photo_dir / f"photo_{i+1}.jpg"
                    img_bgr = cv2.cvtColor(capture['image'], cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(photo_path), img_bgr)
                
                # Clear and go to start
                st.session_state.enrollment_captures = []
                st.session_state.last_photo_signature = None
                st.session_state.camera_input_counter += 1
                st.session_state.step = 'start'
                st.success(f"You're enrolled, {st.session_state.student_name}! Your data is saved online.")
                st.balloons()
                st.rerun()


if __name__ == "__main__":
    main()
