from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    supabase_connected: bool
    models_loaded: bool


class CheckEnrollmentRequest(BaseModel):
    student_id: str
    student_name: str


class CheckEnrollmentResponse(BaseModel):
    exists: bool
    duplicate_id: bool
    duplicate_name: bool
    message: str


class RegisterEnrollmentResponse(BaseModel):
    success: bool
    enrollment_id: Optional[UUID] = None
    message: str


class ProcessAttendanceResponse(BaseModel):
    success: bool
    session_id: Optional[UUID] = None
    total_students_present: int
    total_students_absent: int
    message: str


class ProcessingJobResponse(BaseModel):
    job_id: str
    message: str


class ProcessingProgressResponse(BaseModel):
    job_id: str
    status: str  # "processing", "completed", "error"
    progress: float  # 0.0 to 1.0
    session_id: Optional[UUID] = None
    total_students_present: Optional[int] = None
    total_students_absent: Optional[int] = None
    error: Optional[str] = None


class StudentResponse(BaseModel):
    id: UUID
    student_id: str
    student_name: str
    user_id: UUID
    enrolled_at: Optional[datetime] = None
    status: str
    photo_urls: Optional[List[str]] = None


class StudentListResponse(BaseModel):
    students: List[StudentResponse]
    total: int


class AttendanceSessionResponse(BaseModel):
    id: UUID
    course_id: Optional[UUID] = None
    teacher_id: Optional[UUID] = None
    video_filename: Optional[str] = None
    total_frames: int
    total_students_present: int
    total_students_absent: int
    processing_time_seconds: Optional[float] = None
    processed_at: Optional[datetime] = None
    notes: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    user_id: Optional[UUID] = None
    student_name: str
    student_id: str
    is_present: bool
    confidence_score: Optional[float] = None
    frames_detected: int
    frames_total: int
    best_frame_path: Optional[str] = None


class AttendanceSessionDetailResponse(BaseModel):
    session: AttendanceSessionResponse
    records: List[AttendanceRecordResponse]


class AttendanceHistoryResponse(BaseModel):
    sessions: List[AttendanceSessionResponse]
    total: int
