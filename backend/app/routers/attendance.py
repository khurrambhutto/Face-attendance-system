from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    BackgroundTasks,
)
from typing import Optional
from uuid import UUID
import time
import os
import cv2
from pathlib import Path

from ..models.schemas import (
    ProcessAttendanceResponse,
    AttendanceSessionResponse,
    AttendanceSessionDetailResponse,
    AttendanceRecordResponse,
    AttendanceHistoryResponse,
)
from ..services.detector import get_detector
from ..services.supabase_service import get_supabase_service
from ..config import settings

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def save_best_frame(
    session_id: str, student_id: str, frame_image, frames_dir: Path
) -> str:
    session_dir = frames_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    frame_path = session_dir / f"{student_id}_best.jpg"
    cv2.imwrite(str(frame_path), frame_image)

    return str(frame_path)


@router.post("/process", response_model=ProcessAttendanceResponse)
async def process_attendance(
    background_tasks: BackgroundTasks,
    course_id: str = Form(...),
    teacher_id: str = Form(...),
    video: UploadFile = File(...),
):
    detector = get_detector()
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    if not detector.detector:
        if not detector.initialize():
            raise HTTPException(
                status_code=503, detail="Face detection model not loaded"
            )

    videos_dir = Path(settings.LOCAL_VIDEOS_PATH)
    videos_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(settings.LOCAL_FRAMES_PATH)
    frames_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    video_filename = f"{timestamp}_{course_id}_{video.filename}"
    video_path = videos_dir / video_filename

    contents = await video.read()
    with open(video_path, "wb") as f:
        f.write(contents)

    video_info = detector.get_video_info(str(video_path))
    if not video_info:
        raise HTTPException(status_code=400, detail="Invalid video file")

    enrolled_students = supabase.get_enrolled_students_for_recognition(course_id)

    if not enrolled_students:
        raise HTTPException(
            status_code=400, detail="No students enrolled in this course"
        )

    start_time = time.time()

    result = detector.process_video(str(video_path), enrolled_students)

    processing_time = time.time() - start_time

    recognized = result.get("recognized_students", {})
    best_frames = result.get("best_frames", {})
    total_frames = result.get("frames_processed", 0)

    present_students = []
    for student_id, data in recognized.items():
        frames_detected = data.get("frames_detected", 0)
        confidence = data.get("best_similarity", 0.0)

        if frames_detected > 0 and confidence >= 0.363:
            present_students.append(
                {
                    "student_id": student_id,
                    "student_name": data.get("student_name"),
                    "frames_detected": frames_detected,
                    "confidence": confidence,
                }
            )

    absent_students = []
    for student in enrolled_students:
        sid = student.get("id")
        found = any(p["student_id"] == sid for p in present_students)
        if not found:
            absent_students.append(
                {"student_id": sid, "student_name": student.get("student_name")}
            )

    session_id = supabase.create_attendance_session(
        course_id=course_id,
        teacher_id=teacher_id,
        video_filename=video_filename,
        total_frames=total_frames,
        total_present=len(present_students),
        total_absent=len(absent_students),
        processing_time=processing_time,
    )

    if not session_id:
        raise HTTPException(
            status_code=500, detail="Failed to create attendance session"
        )

    session_id_str = str(session_id)

    for student in present_students:
        best_frame_path = None
        if student["student_id"] in best_frames:
            bf = best_frames[student["student_id"]]
            best_frame_path = save_best_frame(
                session_id_str, student["student_id"], bf["image"], frames_dir
            )

        enrollment = next(
            (s for s in enrolled_students if s.get("id") == student["student_id"]), None
        )

        supabase.create_attendance_record(
            session_id=session_id_str,
            enrollment_id=student["student_id"],
            user_id=enrollment.get("user_id") if enrollment else None,
            student_name=student["student_name"],
            student_id=student["student_id"],
            is_present=True,
            confidence_score=student["confidence"],
            frames_detected=student["frames_detected"],
            frames_total=total_frames,
            best_frame_path=best_frame_path,
        )

    for student in absent_students:
        enrollment = next(
            (s for s in enrolled_students if s.get("id") == student.get("student_id")),
            None,
        )

        supabase.create_attendance_record(
            session_id=session_id_str,
            enrollment_id=student.get("student_id"),
            user_id=enrollment.get("user_id") if enrollment else None,
            student_name=student.get("student_name", ""),
            student_id=student.get("student_id", ""),
            is_present=False,
            confidence_score=0.0,
            frames_detected=0,
            frames_total=total_frames,
        )

    return ProcessAttendanceResponse(
        success=True,
        session_id=session_id,
        total_students_present=len(present_students),
        total_students_absent=len(absent_students),
        message=f"Attendance processed: {len(present_students)} present, {len(absent_students)} absent",
    )


@router.get("/session/{session_id}", response_model=AttendanceSessionDetailResponse)
async def get_attendance_session(session_id: str):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    session = supabase.get_attendance_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    records = supabase.get_attendance_records(session_id)

    session_response = AttendanceSessionResponse(
        id=UUID(session["id"]),
        course_id=UUID(session["course_id"]),
        teacher_id=UUID(session["teacher_id"]),
        video_filename=session.get("video_filename"),
        total_frames=session.get("total_frames", 0),
        total_students_present=session.get("total_students_present", 0),
        total_students_absent=session.get("total_students_absent", 0),
        processing_time_seconds=session.get("processing_time_seconds"),
        processed_at=session.get("processed_at"),
        notes=session.get("notes"),
    )

    records_response = []
    for record in records:
        records_response.append(
            AttendanceRecordResponse(
                id=UUID(record["id"]),
                session_id=UUID(record["session_id"]),
                enrollment_id=UUID(record["enrollment_id"])
                if record.get("enrollment_id")
                else None,
                user_id=UUID(record["user_id"]) if record.get("user_id") else None,
                student_name=record.get("student_name", ""),
                student_id=record.get("student_id", ""),
                is_present=record.get("is_present", False),
                confidence_score=record.get("confidence_score"),
                frames_detected=record.get("frames_detected", 0),
                frames_total=record.get("frames_total", 0),
                best_frame_path=record.get("best_frame_path"),
            )
        )

    return AttendanceSessionDetailResponse(
        session=session_response, records=records_response
    )


@router.get("/history", response_model=AttendanceHistoryResponse)
async def get_attendance_history(
    course_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    sessions = supabase.get_attendance_history(
        course_id=course_id, teacher_id=teacher_id, limit=limit, offset=offset
    )

    sessions_response = []
    for session in sessions:
        sessions_response.append(
            AttendanceSessionResponse(
                id=UUID(session["id"]),
                course_id=UUID(session["course_id"]),
                teacher_id=UUID(session["teacher_id"]),
                video_filename=session.get("video_filename"),
                total_frames=session.get("total_frames", 0),
                total_students_present=session.get("total_students_present", 0),
                total_students_absent=session.get("total_students_absent", 0),
                processing_time_seconds=session.get("processing_time_seconds"),
                processed_at=session.get("processed_at"),
                notes=session.get("notes"),
            )
        )

    return AttendanceHistoryResponse(sessions=sessions_response, total=len(sessions))
