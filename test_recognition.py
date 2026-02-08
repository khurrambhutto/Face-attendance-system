#!/usr/bin/env python3
"""
Simple Face Recognition Test Script
Test if enrolled students are recognized from webcam
"""

import cv2
import json
import numpy as np
from pathlib import Path
from detector import YuNetDetector, init_camera


def load_embeddings():
    """Load enrolled student embeddings"""
    embeddings_file = Path("data/embeddings/embeddings.json")
    
    if not embeddings_file.exists():
        print("❌ No embeddings found. Please enroll students first.")
        print("   Run: streamlit run enrollment_app.py")
        return None
    
    with open(embeddings_file, 'r') as f:
        return json.load(f)


def cosine_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings"""
    embedding1 = np.array(embedding1).flatten()  # Ensure 1D array
    embedding2 = np.array(embedding2).flatten()  # Ensure 1D array
    
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    return dot_product / (norm1 * norm2)


def recognize_face(embedding, embeddings_data, threshold=0.363):
    """
    Match face embedding against enrolled students
    
    Args:
        embedding: Face embedding to match (128D vector)
        embeddings_data: Loaded embeddings JSON data
        threshold: Similarity threshold (default: 0.363 from SFace docs)
    
    Returns:
        (student_id, student_name, similarity) or (None, None, 0)
    """
    best_match = None
    best_similarity = 0
    
    for student_id, student_data in embeddings_data["students"].items():
        # Compare against all enrolled embeddings for this student
        for enrolled_embedding in student_data["embeddings"]:
            similarity = cosine_similarity(embedding, enrolled_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = student_id
    
    if best_similarity >= threshold:
        return best_match, embeddings_data["students"][best_match]["name"], best_similarity
    
    return None, None, best_similarity


def main():
    """Main recognition test"""
    print("\n" + "="*60)
    print("       FACE RECOGNITION TEST")
    print("="*60 + "\n")
    
    # Load embeddings
    embeddings_data = load_embeddings()
    if not embeddings_data:
        return
    
    # Show enrolled students
    print(f"✓ Loaded {len(embeddings_data['students'])} enrolled student(s):")
    for student_id, student_data in embeddings_data["students"].items():
        print(f"  - {student_id}: {student_data['name'].strip()} ({student_data['num_embeddings']} photos)")
    print()
    
    # Initialize detector and recognizer
    print("Initializing models...")
    detector = YuNetDetector()
    
    if not detector.initialize():
        print("❌ Failed to initialize YuNet detector")
        return
    
    if not detector.initialize_sface():
        print("❌ Failed to initialize SFace recognizer")
        return
    
    print("✓ Models initialized\n")
    
    # Initialize camera
    print("Starting camera...")
    cap, backend_name = init_camera()
    if not cap:
        print("❌ Could not access camera")
        return
    
    print(f"✓ Camera started ({backend_name})")
    print("\n" + "="*60)
    print("CONTROLS:")
    print("  - Position your face in front of camera")
    print("  - Press 'q' to quit")
    print("="*60 + "\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect faces
        faces, num_faces = detector.detect_raw(frame)
        
        display_frame = frame.copy()
        
        if faces is not None and num_faces > 0:
            # Process first detected face
            face = faces[0]
            x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            
            # Generate embedding
            embedding = detector.get_face_embedding(frame, face)
            
            if embedding is not None:
                # Try to recognize
                student_id, student_name, similarity = recognize_face(
                    embedding,
                    embeddings_data
                )
                
                # Draw results
                if student_id:
                    # RECOGNIZED!
                    label = f"{student_name.strip()} ({similarity:.2f})"
                    color = (0, 255, 0)  # Green
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                    cv2.putText(display_frame, label, (x, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    cv2.putText(display_frame, f"ID: {student_id}", (x, y + h + 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                else:
                    # NOT RECOGNIZED
                    label = f"Unknown ({similarity:.2f})"
                    color = (0, 0, 255)  # Red
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                    cv2.putText(display_frame, label, (x, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                # Failed to generate embedding
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(display_frame, "No embedding", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        else:
            # No face detected
            cv2.putText(display_frame, "No face detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Show frame
        cv2.imshow('Face Recognition Test', display_frame)
        
        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✓ Test completed")


if __name__ == "__main__":
    main()
