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

    profiles = supabase.get_enrollments(course_id)

    students = []
    for profile in profiles[offset : offset + limit]:
        photo_urls = None
        if profile.get("photo_urls"):
            if isinstance(profile["photo_urls"], list):
                photo_urls = profile["photo_urls"]
            elif isinstance(profile["photo_urls"], dict):
                photo_urls = list(profile["photo_urls"].values())

        students.append(
            StudentResponse(
                id=UUID(profile["id"]),
                student_id=profile.get("student_id", ""),
                student_name=profile.get("name", ""),
                user_id=UUID(profile["id"]),
                enrolled_at=profile.get("created_at"),
                status=profile.get("enrollment_status", "active"),
                photo_urls=photo_urls,
            )
        )

    return StudentListResponse(students=students, total=len(profiles))


@router.get("/{profile_id}", response_model=StudentResponse)
async def get_student(profile_id: str):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    profile = supabase.get_enrollment(profile_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")

    photo_urls = None
    if profile.get("photo_urls"):
        if isinstance(profile["photo_urls"], list):
            photo_urls = profile["photo_urls"]
        elif isinstance(profile["photo_urls"], dict):
            photo_urls = list(profile["photo_urls"].values())

    return StudentResponse(
        id=UUID(profile["id"]),
        student_id=profile.get("student_id", ""),
        student_name=profile.get("name", ""),
        user_id=UUID(profile["id"]),
        enrolled_at=profile.get("created_at"),
        status=profile.get("enrollment_status", "active"),
        photo_urls=photo_urls,
    )


@router.delete("/{profile_id}")
async def delete_student(profile_id: str):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    profile = supabase.get_enrollment(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")

    success = supabase.delete_enrollment(profile_id)

    if success:
        return {"success": True, "message": "Student enrollment deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete student")
