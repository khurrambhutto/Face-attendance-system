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
    
    # Show enrollment status
    if embeddings:
        num_students = len(embeddings.get("students", {}))
        student_names = [s["name"].strip() for s in embeddings["students"].values()]
        st.success(f"✅ {num_students} enrolled student(s): **{', '.join(student_names)}**")
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
            
            # Show recognized students summary
            recognized = results.get('recognized_students', {})
            if recognized:
                st.header("🎓 Recognized Students")
                for sid, info in recognized.items():
                    st.write(f"✅ **{info['name']}** (ID: {sid}) — best match: {info['similarity']:.0%}")
            elif embeddings:
                st.info("No enrolled students were recognized in this video.")
            
            # Top 3 frames
            st.header("🖼️ Top 3 Frames with Most Faces")
            
            if results['top_frames']:
                for i, frame_data in enumerate(results['top_frames']):
                    with st.container():
                        col_frame, col_info = st.columns([3, 1])
                        with col_frame:
                            st.image(
                                frame_data['image'],
                                caption=f"Frame #{frame_data['frame_num']}",
                                use_container_width=True
                            )
                        with col_info:
                            st.metric(
                                f"Frame #{i+1}",
                                f"{frame_data['face_count']} faces",
                                label_visibility="visible"
                            )
                            st.write(f"**Frame Number:** {frame_data['frame_num']}")
                            st.write(f"**Faces Detected:** {frame_data['face_count']}")
                            # Show who was recognized in this frame
                            if frame_data.get('recognized'):
                                st.write("**Recognized:**")
                                for r in frame_data['recognized']:
                                    st.write(f"  • {r['name']} ({r['similarity']:.0%})")
                    st.divider()
            else:
                st.info("No faces detected in the video")
        
        # Clean up temp file
        import os
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
    
    else:
        st.info("👆 Upload a video file to begin face detection & recognition")


if __name__ == "__main__":
    main()
