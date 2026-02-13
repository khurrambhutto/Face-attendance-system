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

    def check_enrollment_exists(
        self, student_id: str, student_name: str
    ) -> Dict[str, Any]:
        result = {"exists": False, "duplicate_id": False, "duplicate_name": False}

        normalized_name = " ".join(student_name.strip().lower().split())

        id_response = (
            self.client.table("enrollments")
            .select("id")
            .eq("student_id", student_id.strip())
            .execute()
        )
        if id_response.data:
            result["exists"] = True
            result["duplicate_id"] = True
            return result

        all_enrollments = (
            self.client.table("enrollments").select("student_name").execute()
        )
        for enrollment in all_enrollments.data or []:
            existing_name = enrollment.get("student_name", "")
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
    ) -> Optional[UUID]:
        try:
            profile_check = (
                self.client.table("profiles").select("id").eq("id", user_id).execute()
            )
            user_id_to_insert = user_id if profile_check.data else None

            response = (
                self.client.table("enrollments")
                .insert(
                    {
                        "user_id": user_id_to_insert,
                        "student_id": student_id.strip(),
                        "student_name": student_name.strip(),
                        "embeddings": embeddings,
                        "photo_urls": photo_urls,
                        "status": "active",
                    }
                )
                .execute()
            )

            if response.data:
                return UUID(response.data[0]["id"])
            return None
        except Exception as e:
            print(f"Failed to create enrollment: {e}")
            return None

    def get_enrollments(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if course_id:
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

                enrollments = []
                for uid in user_ids:
                    response = (
                        self.client.table("enrollments")
                        .select("*")
                        .eq("user_id", uid)
                        .eq("status", "active")
                        .execute()
                    )
                    if response.data:
                        enrollments.extend(response.data)
                return enrollments
            else:
                response = (
                    self.client.table("enrollments")
                    .select("*")
                    .eq("status", "active")
                    .order("created_at", desc=True)
                    .execute()
                )
                return response.data or []
        except Exception as e:
            print(f"Failed to get enrollments: {e}")
            return []

    def get_enrollment(self, enrollment_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.client.table("enrollments")
                .select("*")
                .eq("id", enrollment_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            print(f"Failed to get enrollment: {e}")
            return None

    def get_enrollment_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.client.table("enrollments")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "active")
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    def delete_enrollment(self, enrollment_id: str) -> bool:
        try:
            self.client.table("enrollments").update({"status": "deleted"}).eq(
                "id", enrollment_id
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to delete enrollment: {e}")
            return False

    def get_enrolled_students_for_recognition(
        self, course_id: str
    ) -> List[Dict[str, Any]]:
        try:
            course_enrollments = (
                self.client.table("course_enrollments")
                .select("user_id, student_id")
                .eq("course_id", course_id)
                .eq("status", "active")
                .execute()
            )

            students = []
            for ce in course_enrollments.data or []:
                user_id = ce.get("user_id")
                if user_id:
                    enrollment = self.get_enrollment_by_user(user_id)
                    if enrollment:
                        students.append(
                            {
                                "id": enrollment["id"],
                                "user_id": enrollment.get("user_id"),
                                "student_id": enrollment.get("student_id"),
                                "student_name": enrollment.get("student_name"),
                                "embeddings": enrollment.get("embeddings", []),
                            }
                        )

            return students
        except Exception as e:
            print(f"Failed to get enrolled students: {e}")
            return []

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
        enrollment_id: Optional[str],
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
                    "enrollment_id": enrollment_id,
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
