from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID

from ..models.schemas import StudentResponse, StudentListResponse
from ..services.supabase_service import get_supabase_service

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
async def list_students(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    enrollments = supabase.get_enrollments(course_id)

    students = []
    for enrollment in enrollments[offset : offset + limit]:
        photo_urls = None
        if enrollment.get("photo_urls"):
            if isinstance(enrollment["photo_urls"], list):
                photo_urls = enrollment["photo_urls"]
            elif isinstance(enrollment["photo_urls"], dict):
                photo_urls = list(enrollment["photo_urls"].values())

        students.append(
            StudentResponse(
                id=UUID(enrollment["id"]),
                student_id=enrollment.get("student_id", ""),
                student_name=enrollment.get("student_name", ""),
                user_id=UUID(enrollment["user_id"])
                if enrollment.get("user_id")
                else None,
                enrolled_at=enrollment.get("created_at"),
                status=enrollment.get("status", "active"),
                photo_urls=photo_urls,
            )
        )

    return StudentListResponse(students=students, total=len(enrollments))


@router.get("/{enrollment_id}", response_model=StudentResponse)
async def get_student(enrollment_id: str):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    enrollment = supabase.get_enrollment(enrollment_id)

    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not found")

    photo_urls = None
    if enrollment.get("photo_urls"):
        if isinstance(enrollment["photo_urls"], list):
            photo_urls = enrollment["photo_urls"]
        elif isinstance(enrollment["photo_urls"], dict):
            photo_urls = list(enrollment["photo_urls"].values())

    return StudentResponse(
        id=UUID(enrollment["id"]),
        student_id=enrollment.get("student_id", ""),
        student_name=enrollment.get("student_name", ""),
        user_id=UUID(enrollment["user_id"]) if enrollment.get("user_id") else None,
        enrolled_at=enrollment.get("created_at"),
        status=enrollment.get("status", "active"),
        photo_urls=photo_urls,
    )


@router.delete("/{enrollment_id}")
async def delete_student(enrollment_id: str):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    enrollment = supabase.get_enrollment(enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not found")

    success = supabase.delete_enrollment(enrollment_id)

    if success:
        return {"success": True, "message": "Student enrollment deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete student")
