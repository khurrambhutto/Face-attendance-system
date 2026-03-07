from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
)
from typing import Optional, Dict
from uuid import UUID
import time
import threading
import uuid
import cv2
from pathlib import Path

from ..models.schemas import (
    ProcessingJobResponse,
    ProcessingProgressResponse,
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

# In-memory job tracker
processing_jobs: Dict[str, dict] = {}


def save_best_frame(
    session_id: str, student_id: str, frame_image, frames_dir: Path
) -> str:
    session_dir = frames_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    frame_path = session_dir / f"{student_id}_best.jpg"
    cv2.imwrite(str(frame_path), frame_image)

    return str(frame_path)


def _process_video_in_background(
    job_id: str,
    video_path: str,
    course_id: str,
    teacher_id: str,
    video_filename: str,
):
    """Run video processing in a background thread with progress updates."""
    detector = get_detector()
    supabase = get_supabase_service()
    frames_dir = Path(settings.LOCAL_FRAMES_PATH)
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        enrolled_students = supabase.get_enrolled_students_for_recognition(course_id)

        if not enrolled_students:
            processing_jobs[job_id].update({
                "status": "error",
                "error": "No students enrolled in this course",
            })
            return

        start_time = time.time()

        def progress_callback(progress: float):
            processing_jobs[job_id]["progress"] = round(progress, 3)

        result = detector.process_video(
            video_path,
            enrolled_students,
            progress_callback=progress_callback,
        )

        if "error" in result:
            processing_jobs[job_id].update({
                "status": "error",
                "error": result["error"],
            })
            return

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
            processing_jobs[job_id].update({
                "status": "error",
                "error": "Failed to create attendance session",
            })
            return

        session_id_str = str(session_id)

        for student in present_students:
            best_frame_path = None
            if student["student_id"] in best_frames:
                bf = best_frames[student["student_id"]]
                best_frame_path = save_best_frame(
                    session_id_str, student["student_id"], bf["image"], frames_dir
                )

            enrollment = next(
                (s for s in enrolled_students if s.get("id") == student["student_id"]),
                None,
            )

            supabase.create_attendance_record(
                session_id=session_id_str,
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
                (
                    s
                    for s in enrolled_students
                    if s.get("id") == student.get("student_id")
                ),
                None,
            )

            supabase.create_attendance_record(
                session_id=session_id_str,
                user_id=enrollment.get("user_id") if enrollment else None,
                student_name=student.get("student_name", ""),
                student_id=student.get("student_id", ""),
                is_present=False,
                confidence_score=0.0,
                frames_detected=0,
                frames_total=total_frames,
            )

        processing_jobs[job_id].update({
            "status": "completed",
            "progress": 1.0,
            "session_id": session_id,
            "total_students_present": len(present_students),
            "total_students_absent": len(absent_students),
        })

    except Exception as e:
        processing_jobs[job_id].update({
            "status": "error",
            "error": str(e),
        })


@router.post("/process", response_model=ProcessingJobResponse)
async def process_attendance(
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

    timestamp = int(time.time())
    video_filename = f"{timestamp}_{course_id}_{video.filename}"
    video_path = videos_dir / video_filename

    contents = await video.read()
    with open(video_path, "wb") as f:
        f.write(contents)

    video_info = detector.get_video_info(str(video_path))
    if not video_info:
        raise HTTPException(status_code=400, detail="Invalid video file")

    # Create a job and start processing in background
    job_id = str(uuid.uuid4())
    processing_jobs[job_id] = {
        "status": "processing",
        "progress": 0.0,
        "session_id": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_process_video_in_background,
        args=(job_id, str(video_path), course_id, teacher_id, video_filename),
        daemon=True,
    )
    thread.start()

    return ProcessingJobResponse(
        job_id=job_id,
        message="Processing started",
    )


@router.get("/progress/{job_id}", response_model=ProcessingProgressResponse)
async def get_processing_progress(job_id: str):
    job = processing_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ProcessingProgressResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        session_id=job.get("session_id"),
        total_students_present=job.get("total_students_present"),
        total_students_absent=job.get("total_students_absent"),
        error=job.get("error"),
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
