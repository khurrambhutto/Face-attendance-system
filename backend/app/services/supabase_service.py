from typing import Optional, List, Dict, Any
from uuid import UUID
from supabase import create_client, Client
from ..config import settings


class SupabaseService:
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self.client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
            )
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize Supabase: {e}")
            return False

    def is_initialized(self) -> bool:
        return self._initialized

    # ── Profile / Enrollment Methods ──────────────────────────────

    def check_enrollment_exists(
        self, student_id: str, student_name: str
    ) -> Dict[str, Any]:
        """Check if a student_id or name is already taken in profiles."""
        result = {"exists": False, "duplicate_id": False, "duplicate_name": False}

        # Check student_id
        id_response = (
            self.client.table("profiles")
            .select("id")
            .eq("student_id", student_id.strip())
            .execute()
        )
        if id_response.data:
            result["exists"] = True
            result["duplicate_id"] = True
            return result

        # Check name (normalized comparison)
        normalized_name = " ".join(student_name.strip().lower().split())
        all_profiles = (
            self.client.table("profiles")
            .select("name")
            .not_.is_("name", "null")
            .execute()
        )
        for profile in all_profiles.data or []:
            existing_name = profile.get("name", "")
            if existing_name:
                normalized_existing = " ".join(existing_name.strip().lower().split())
                if normalized_existing == normalized_name:
                    result["exists"] = True
                    result["duplicate_name"] = True
                    return result

        return result

    def create_enrollment(
        self,
        user_id: str,
        student_id: str,
        student_name: str,
        embeddings: List[List[float]],
        photo_urls: List[str],
    ) -> bool:
        """Update a profile row with face enrollment data."""
        try:
            if not user_id or not user_id.strip():
                print("Failed to create enrollment: user_id is required")
                return False

            response = (
                self.client.table("profiles")
                .update(
                    {
                        "student_id": student_id.strip(),
                        "name": student_name.strip(),
                        "embeddings": embeddings,
                        "photo_urls": photo_urls,
                        "enrollment_status": "active",
                    }
                )
                .eq("id", user_id.strip())
                .execute()
            )

            if response.data:
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to create enrollment: {e}")
            print(f"[DEBUG] user_id={user_id}, student_id={student_id}")
            import traceback
            traceback.print_exc()
            return False

    def get_enrollments(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get enrolled students (profiles with active enrollment_status)."""
        try:
            if course_id:
                # Get user_ids enrolled in this course
                course_students = (
                    self.client.table("course_enrollments")
                    .select("user_id")
                    .eq("course_id", course_id)
                    .eq("status", "active")
                    .execute()
                )
                user_ids = [cs["user_id"] for cs in course_students.data or []]

                if not user_ids:
                    return []

                profiles = []
                for uid in user_ids:
                    response = (
                        self.client.table("profiles")
                        .select("*")
                        .eq("id", uid)
                        .eq("enrollment_status", "active")
                        .execute()
                    )
                    if response.data:
                        profiles.extend(response.data)
                return profiles
            else:
                response = (
                    self.client.table("profiles")
                    .select("*")
                    .eq("enrollment_status", "active")
                    .eq("role", "student")
                    .order("created_at", desc=True)
                    .execute()
                )
                return response.data or []
        except Exception as e:
            print(f"Failed to get enrollments: {e}")
            return []

    def get_enrollment(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a single enrolled student profile."""
        try:
            response = (
                self.client.table("profiles")
                .select("*")
                .eq("id", profile_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            print(f"Failed to get enrollment: {e}")
            return None

    def get_enrollment_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get enrollment data for a specific user."""
        try:
            response = (
                self.client.table("profiles")
                .select("*")
                .eq("id", user_id)
                .eq("enrollment_status", "active")
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    def delete_enrollment(self, profile_id: str) -> bool:
        """Soft-delete enrollment by resetting face data."""
        try:
            self.client.table("profiles").update(
                {
                    "enrollment_status": "deleted",
                    "embeddings": None,
                    "photo_urls": None,
                }
            ).eq("id", profile_id).execute()
            return True
        except Exception as e:
            print(f"Failed to delete enrollment: {e}")
            return False

    def get_enrolled_students_for_recognition(
        self, course_id: str
    ) -> List[Dict[str, Any]]:
        """Get students enrolled in a course with their face embeddings."""
        try:
            course_enrollments = (
                self.client.table("course_enrollments")
                .select("user_id")
                .eq("course_id", course_id)
                .eq("status", "active")
                .execute()
            )

            students = []
            for ce in course_enrollments.data or []:
                user_id = ce.get("user_id")
                if user_id:
                    profile = self.get_enrollment_by_user(user_id)
                    if profile:
                        students.append(
                            {
                                "id": profile["id"],
                                "user_id": profile["id"],
                                "student_id": profile.get("student_id"),
                                "student_name": profile.get("name"),
                                "embeddings": profile.get("embeddings", []),
                            }
                        )

            return students
        except Exception as e:
            print(f"Failed to get enrolled students: {e}")
            return []

    # ── Attendance Methods ────────────────────────────────────────

    def create_attendance_session(
        self,
        course_id: str,
        teacher_id: str,
        video_filename: str,
        total_frames: int,
        total_present: int,
        total_absent: int,
        processing_time: float,
    ) -> Optional[UUID]:
        try:
            response = (
                self.client.table("attendance_sessions")
                .insert(
                    {
                        "course_id": course_id,
                        "teacher_id": teacher_id,
                        "video_filename": video_filename,
                        "total_frames": total_frames,
                        "total_students_present": total_present,
                        "total_students_absent": total_absent,
                        "processing_time_seconds": processing_time,
                    }
                )
                .execute()
            )

            if response.data:
                return UUID(response.data[0]["id"])
            return None
        except Exception as e:
            print(f"Failed to create attendance session: {e}")
            return None

    def create_attendance_record(
        self,
        session_id: str,
        user_id: Optional[str],
        student_name: str,
        student_id: str,
        is_present: bool,
        confidence_score: float,
        frames_detected: int,
        frames_total: int,
        best_frame_path: Optional[str] = None,
    ) -> bool:
        try:
            self.client.table("attendance_records").insert(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "student_name": student_name,
                    "student_id": student_id,
                    "is_present": is_present,
                    "confidence_score": confidence_score,
                    "frames_detected": frames_detected,
                    "frames_total": frames_total,
                    "best_frame_path": best_frame_path,
                }
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to create attendance record: {e}")
            return False

    def get_attendance_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.client.table("attendance_sessions")
                .select("*")
                .eq("id", session_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            print(f"Failed to get attendance session: {e}")
            return None

    def get_attendance_records(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            response = (
                self.client.table("attendance_records")
                .select("*")
                .eq("session_id", session_id)
                .order("student_name")
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Failed to get attendance records: {e}")
            return []

    def get_attendance_history(
        self,
        course_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            query = self.client.table("attendance_sessions").select("*")

            if course_id:
                query = query.eq("course_id", course_id)
            if teacher_id:
                query = query.eq("teacher_id", teacher_id)

            response = (
                query.order("processed_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Failed to get attendance history: {e}")
            return []

    # ── Storage Methods ───────────────────────────────────────────

    def upload_photo(
        self, file_path: str, file_content: bytes, content_type: str = "image/jpeg"
    ) -> Optional[str]:
        try:
            bucket = self.client.storage.from_(settings.SUPABASE_BUCKET)
            bucket.upload(file_path, file_content, {"content-type": content_type})

            public_url = bucket.get_public_url(file_path)
            if isinstance(public_url, str):
                return public_url
            elif isinstance(public_url, dict):
                return public_url.get("publicUrl") or public_url.get("publicURL")
            return None
        except Exception as e:
            print(f"Failed to upload photo: {e}")
            return None


supabase_service = SupabaseService()


def get_supabase_service() -> SupabaseService:
    return supabase_service
