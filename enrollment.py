#!/usr/bin/env python3
"""
Face Enrollment System
Capture face images from webcam and generate SFace embeddings
"""

import cv2
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from detector import YuNetDetector, init_camera


class FaceEnrollment:
    """Handle face enrollment process"""
    
    def __init__(self, embeddings_file: str = "embeddings.json"):
        self.embeddings_file = Path(embeddings_file)
        self.detector = YuNetDetector()
        self.embeddings_data = self.load_embeddings()
        
    def load_embeddings(self) -> dict:
        """Load existing embeddings from file"""
        if self.embeddings_file.exists():
            with open(self.embeddings_file, 'r') as f:
                return json.load(f)
        return {"students": {}}
    
    def save_embeddings(self):
        """Save embeddings to file"""
        with open(self.embeddings_file, 'w') as f:
            json.dump(self.embeddings_data, f, indent=2)
        print(f"✓ Embeddings saved to {self.embeddings_file}")
    
    def check_face_quality(self, frame: np.ndarray, face: np.ndarray) -> bool:
        """Check if detected face meets quality requirements
        
        Args:
            frame: Input image
            face: Face detection from YuNet
            
        Returns:
            True if face quality is acceptable
        """
        x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
        
        # Check face size (minimum 100x100 pixels)
        if w < 100 or h < 100:
            return False
        
        # Check if face is reasonably centered in frame
        frame_h, frame_w = frame.shape[:2]
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Face center should be within middle 50% of frame
        if not (frame_w * 0.25 < center_x < frame_w * 0.75):
            return False
        if not (frame_h * 0.25 < center_y < frame_h * 0.75):
            return False
        
        return True
    
    def capture_photos(self, student_id: str, student_name: str, num_photos: int = 3) -> bool:
        """Capture face photos and generate embeddings
        
        Args:
            student_id: Unique student identifier
            student_name: Student's full name
            num_photos: Number of photos to capture (default: 3)
            
        Returns:
            True if enrollment successful
        """
        # Initialize models
        if not self.detector.initialize():
            print("✗ Failed to initialize YuNet detector")
            return False
        
        if not self.detector.initialize_sface():
            print("✗ Failed to initialize SFace recognizer")
            return False
        
        # Initialize camera
        cap, backend_name = init_camera()
        if not cap:
            print("✗ Failed to open camera")
            return False
        
        print(f"\n{'='*60}")
        print(f"Enrolling: {student_name} (ID: {student_id})")
        print(f"Camera: {backend_name}")
        print(f"Photos needed: {num_photos}")
        print(f"{'='*60}\n")
        
        captured_photos = []
        photo_count = 0
        
        print("Instructions:")
        print("- Position your face in the center of the frame")
        print("- Keep good lighting on your face")
        print("- Press SPACE to capture each photo")
        print("- Press 'q' to quit\n")
        
        while photo_count < num_photos:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Detect faces
            faces, num_faces = self.detector.detect_raw(frame)
            
            # Draw detection box
            display_frame = frame.copy()
            
            if faces is not None and num_faces > 0:
                # Use first detected face
                face = faces[0]
                x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                
                # Check quality
                is_good_quality = self.check_face_quality(frame, face)
                
                # Color based on quality
                box_color = (0, 255, 0) if is_good_quality else (0, 0, 255)
                
                # Draw bounding box
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), box_color, 2)
                
                # Add status text
                status = "GOOD - Press SPACE" if is_good_quality else "Move closer/center"
                cv2.putText(display_frame, status, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
                
                # Add photo counter
                cv2.putText(display_frame, f"Photos: {photo_count}/{num_photos}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            else:
                cv2.putText(display_frame, "No face detected", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Show frame
            cv2.imshow('Face Enrollment', display_frame)
            
            # Handle keyboard
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n✗ Enrollment cancelled by user")
                cap.release()
                cv2.destroyAllWindows()
                return False
            
            if key == ord(' ') and faces is not None and num_faces > 0:
                face = faces[0]
                
                # Check quality before capturing
                if self.check_face_quality(frame, face):
                    # Generate embedding
                    embedding = self.detector.get_face_embedding(frame, face)
                    
                    if embedding is not None:
                        captured_photos.append(embedding.tolist())
                        photo_count += 1
                        print(f"✓ Photo {photo_count}/{num_photos} captured")
                        
                        # Flash effect
                        cv2.putText(display_frame, "CAPTURED!", (frame.shape[1]//2 - 100, frame.shape[0]//2),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                        cv2.imshow('Face Enrollment', display_frame)
                        cv2.waitKey(500)
                    else:
                        print("✗ Failed to generate embedding")
                else:
                    print("✗ Face quality not good enough - move closer to center")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Save embeddings
        if len(captured_photos) == num_photos:
            self.embeddings_data["students"][student_id] = {
                "name": student_name,
                "embeddings": captured_photos,
                "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "num_embeddings": num_photos
            }
            self.save_embeddings()
            
            print(f"\n{'='*60}")
            print(f"✓ Enrollment complete!")
            print(f"  Student: {student_name}")
            print(f"  ID: {student_id}")
            print(f"  Photos captured: {num_photos}")
            print(f"  Embeddings saved: {len(captured_photos)}")
            print(f"{'='*60}\n")
            
            return True
        else:
            print(f"\n✗ Enrollment incomplete: only {len(captured_photos)}/{num_photos} photos captured")
            return False
    
    def list_students(self):
        """List all enrolled students"""
        if not self.embeddings_data["students"]:
            print("No students enrolled yet.")
            return
        
        print(f"\n{'='*60}")
        print("Enrolled Students:")
        print(f"{'='*60}")
        
        for student_id, data in self.embeddings_data["students"].items():
            print(f"ID: {student_id}")
            print(f"  Name: {data['name']}")
            print(f"  Embeddings: {data['num_embeddings']}")
            print(f"  Enrolled: {data['enrolled_at']}")
            print()


def main():
    """Main enrollment interface"""
    print("\n" + "="*60)
    print("       FACE ENROLLMENT SYSTEM")
    print("="*60 + "\n")
    
    enrollment = FaceEnrollment()
    
    while True:
        print("Options:")
        print("1. Enroll new student")
        print("2. List enrolled students")
        print("3. Quit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            student_id = input("Enter student ID: ").strip()
            student_name = input("Enter student name: ").strip()
            
            if not student_id or not student_name:
                print("✗ ID and name are required!")
                continue
            
            if student_id in enrollment.embeddings_data["students"]:
                overwrite = input(f"Student {student_id} already exists. Overwrite? (y/n): ").strip().lower()
                if overwrite != 'y':
                    continue
            
            num_photos = input("Number of photos to capture (default: 3): ").strip()
            try:
                num_photos = int(num_photos) if num_photos else 3
            except ValueError:
                num_photos = 3
            
            enrollment.capture_photos(student_id, student_name, num_photos)
        
        elif choice == '2':
            enrollment.list_students()
        
        elif choice == '3':
            print("\nGoodbye!")
            break
        
        else:
            print("✗ Invalid choice. Try again.")


if __name__ == "__main__":
    main()
