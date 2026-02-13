from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID
import cv2
import numpy as np
from datetime import datetime
import uuid as uuid_lib

from ..models.schemas import (
    CheckEnrollmentRequest,
    CheckEnrollmentResponse,
    RegisterEnrollmentResponse,
)
from ..services.detector import get_detector
from ..services.supabase_service import get_supabase_service
from ..config import settings

router = APIRouter(prefix="/api/enrollment", tags=["enrollment"])


@router.post("/check", response_model=CheckEnrollmentResponse)
async def check_enrollment(request: CheckEnrollmentRequest):
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    student_id = request.student_id.strip()
    student_name = request.student_name.strip()

    if not student_id or not student_name:
        raise HTTPException(status_code=400, detail="Student ID and name are required")

    result = supabase.check_enrollment_exists(student_id, student_name)

    message = "Student ID and name are available"
    if result["duplicate_id"]:
        message = f"Student ID '{student_id}' is already registered"
    elif result["duplicate_name"]:
        message = f"Name '{student_name}' is already enrolled"

    return CheckEnrollmentResponse(
        exists=result["exists"],
        duplicate_id=result["duplicate_id"],
        duplicate_name=result["duplicate_name"],
        message=message,
    )


@router.post("/register", response_model=RegisterEnrollmentResponse)
async def register_enrollment(
    user_id: str = Form(...),
    student_id: str = Form(...),
    student_name: str = Form(...),
    photo_1: UploadFile = File(...),
    photo_2: UploadFile = File(...),
    photo_3: UploadFile = File(...),
):
    detector = get_detector()
    supabase = get_supabase_service()

    if not supabase.is_initialized():
        raise HTTPException(status_code=503, detail="Database not available")

    check_result = supabase.check_enrollment_exists(student_id, student_name)
    if check_result["exists"]:
        msg = (
            "Student ID already registered"
            if check_result["duplicate_id"]
            else "Name already enrolled"
        )
        raise HTTPException(status_code=409, detail=msg)

    photos = [photo_1, photo_2, photo_3]
    embeddings_list = []
    photo_urls = []

    enrollment_uuid = str(uuid_lib.uuid4())

    for i, photo in enumerate(photos):
        contents = await photo.read()

        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(
                status_code=400, detail=f"Invalid image format for photo {i + 1}"
            )

        faces, face_count = detector.detect_faces(frame)

        if faces is None or face_count == 0:
            raise HTTPException(
                status_code=400, detail=f"No face detected in photo {i + 1}"
            )

        if face_count > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Multiple faces detected in photo {i + 1}. Please ensure only one face is visible.",
            )

        embedding = detector.get_face_embedding(frame, faces[0])
        if embedding is None:
            raise HTTPException(
                status_code=400,
                detail=f"Could not generate embedding for photo {i + 1}",
            )

        embeddings_list.append(embedding.tolist()[0])

        file_path = f"{student_id.strip()}/{enrollment_uuid}/photo_{i + 1}.jpg"
        photo_url = supabase.upload_photo(file_path, contents, "image/jpeg")

        if photo_url:
            photo_urls.append(photo_url)
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload photo {i + 1}"
            )

    enrollment_id = supabase.create_enrollment(
        user_id=user_id.strip(),
        student_id=student_id.strip(),
        student_name=student_name.strip(),
        embeddings=embeddings_list,
        photo_urls=photo_urls,
    )

    if enrollment_id:
        return RegisterEnrollmentResponse(
            success=True,
            enrollment_id=enrollment_id,
            message=f"Successfully enrolled {student_name}",
        )
    else:
        raise HTTPException(
            status_code=500, detail="Failed to save enrollment to database"
        )
