"""
Face Detection & Recognition App with Streamlit
Video upload UI - Process video, detect faces, and show recognized student names
"""

import streamlit as st
from detector import YuNetDetector


def main():
    """Main Streamlit app"""
    
    # Page config
    st.set_page_config(
        page_title="Face Detection & Recognition",
        page_icon="😊",
        layout="wide"
    )
    
    # Initialize detector
    if 'detector' not in st.session_state:
        with st.spinner("Loading models..."):
            st.session_state.detector = YuNetDetector()
            st.session_state.detector_initialized = st.session_state.detector.initialize()
            st.session_state.detector.initialize_sface()
            st.session_state.embeddings = st.session_state.detector.load_embeddings()
    
    detector = st.session_state.detector
    embeddings = st.session_state.embeddings
    
    # Title
    st.title("😊 Face Detection & Recognition")
    st.write("Upload a video to detect and recognize faces")
    
    # Show enrollment status with management dropdown
    if embeddings and embeddings.get("students"):
        num_students = len(embeddings["students"])
        student_names = [s["name"].strip() for s in embeddings["students"].values()]
        st.success(f"✅ {num_students} enrolled student(s): **{', '.join(student_names)}**")
        
        # Load metadata for enrollment dates
        from pathlib import Path
        metadata_file = Path("data/metadata/student_info.json")
        metadata = {}
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        with st.expander("👥 Manage Enrolled Students", expanded=False):
            for sid, sdata in list(embeddings["students"].items()):
                col_name, col_id, col_date, col_btn = st.columns([3, 1, 2, 1])
                with col_name:
                    st.write(f"**{sdata['name'].strip()}**")
                with col_id:
                    st.write(f"ID: {sid}")
                with col_date:
                    enrolled_at = metadata.get(sid, {}).get("enrolled_at", "—")
                    st.write(f"📅 {enrolled_at}")
                with col_btn:
                    if st.button("🗑️ Remove", key=f"del_{sid}"):
                        success = detector.delete_student(sid)
                        if success:
                            # Refresh cached embeddings
                            st.session_state.embeddings = detector.load_embeddings()
                            st.success(f"Removed {sdata['name'].strip()}")
                            st.rerun()
                        else:
                            st.error(f"Failed to remove student {sid}")
    else:
        st.warning("⚠️ No enrolled students found. Faces will be detected but not recognized. Run `streamlit run enrollment_app.py` to enroll students first.")
    
    # Video upload section
    st.header("📤 Upload Video")
    
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'avi', 'mov', 'mkv', 'wmv'],
        help="Supported formats: MP4, AVI, MOV, MKV, WMV"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        temp_video_path = f"temp_video.{uploaded_file.name.split('.')[-1]}"
        with open(temp_video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Get video info
        with st.spinner("Analyzing video..."):
            video_info = detector.extract_frame_info(temp_video_path)
        
        if video_info:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Duration", f"{video_info['duration']}s")
            with col2:
                st.metric("Total Frames", video_info['frame_count'])
            with col3:
                st.metric("Resolution", f"{video_info['width']}x{video_info['height']}")
            with col4:
                st.metric("FPS", video_info['fps'])
        
        # Process button
        st.subheader("🚀 Process Video")
        if st.button("Detect & Recognize Faces", type="primary"):
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(progress):
                progress_bar.progress(progress)
                status_text.text(f"Processing... {int(progress * 100)}%")
            
            # Process video with recognition
            with st.spinner("Detecting and recognizing faces..."):
                results = detector.process_video_with_recognition(
                    temp_video_path,
                    embeddings_data=embeddings,
                    progress_callback=update_progress
                )
            
            progress_bar.progress(1.0)
            status_text.text("✓ Processing complete!")
            
            # Store results in session state so they persist across reruns
            st.session_state.results = results
        
        # Display results from session state (persists when dropdown changes)
        if 'results' in st.session_state and st.session_state.results:
            results = st.session_state.results
            
            # Display results
            st.header("📊 Results")
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Frames", results['total_frames'])
            with col2:
                st.metric("Max Faces", results['max_faces'])
            with col3:
                st.metric("Avg Faces", results['avg_faces'])
            with col4:
                st.metric("Total Detections", results['total_face_detections'])
            
            # Attendance Summary with confidence scores
            recognized = results.get('recognized_students', {})
            frames_processed = results.get('frames_processed', results['total_frames'])
            
            st.header("🎓 Attendance Summary")
            
            if recognized:
                st.write(f"**{len(recognized)}** student(s) recognized across **{frames_processed}** frames:")
                st.write("")
                
                for sid, info in sorted(recognized.items(), key=lambda x: x[1]['frames_appeared'], reverse=True):
                    appeared = info['frames_appeared']
                    confidence = appeared / frames_processed if frames_processed > 0 else 0
                    
                    col_status, col_name, col_conf, col_bar = st.columns([0.5, 2, 1.5, 3])
                    with col_status:
                        st.write("✅" if confidence >= 0.02 else "⚠️")
                    with col_name:
                        st.write(f"**{info['name']}** (ID: {sid})")
                    with col_conf:
                        st.write(f"{appeared}/{frames_processed} frames ({confidence:.1%})")
                    with col_bar:
                        st.progress(min(confidence * 5, 1.0))  # Scale up for visibility (20% fills bar)
                
                st.divider()
                
                # Show enrolled but NOT recognized students
                if embeddings and embeddings.get("students"):
                    absent = []
                    for sid, sdata in embeddings["students"].items():
                        if sid not in recognized:
                            absent.append(sdata["name"].strip())
                    if absent:
                        st.write("**❌ Not detected (absent):**")
                        for name in absent:
                            st.write(f"  • {name}")
            elif embeddings:
                st.info("No enrolled students were recognized in this video.")
            
            # Camera tip
            st.info("💡 **Tip for large classes:** Slowly pan/sweep the camera across the room during recording. "
                    "The system aggregates faces across ALL frames — each student only needs to appear in a few frames to be marked present.")
            
            # Best Frame Per Student (with dropdown selector)
            best_frames = results.get('best_frames', {})
            
            if best_frames:
                st.header("🖼️ Best Frame Per Student")
                
                # Build dropdown options: "Name (ID: X)"
                options = {sid: f"{fdata['name']} (ID: {sid})" for sid, fdata in best_frames.items()}
                selected_sid = st.selectbox(
                    "Select a student to view their best detected frame:",
                    options.keys(),
                    format_func=lambda x: options[x]
                )
                
                if selected_sid:
                    fdata = best_frames[selected_sid]
                    col_frame, col_info = st.columns([3, 1])
                    with col_frame:
                        st.image(
                            fdata['image'],
                            caption=f"Frame #{fdata['frame_num']}",
                            width="stretch"
                        )
                    with col_info:
                        st.write(f"### {fdata['name']}")
                        st.write(f"**Student ID:** {selected_sid}")
                        st.write(f"**Best Match:** {fdata['similarity']:.0%}")
                        st.write(f"**Frame:** #{fdata['frame_num']}")
            else:
                st.info("No faces were recognized in the video.")
    
    else:
        st.info("👆 Upload a video file to begin face detection & recognition")


if __name__ == "__main__":
    main()
