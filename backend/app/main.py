from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from .config import settings
from .models.schemas import HealthResponse
from .routers import enrollment, students, attendance
from .services.detector import get_detector
from .services.supabase_service import get_supabase_service

app = FastAPI(
    title="MARK Attendance API",
    description="Face recognition-based attendance system backend",
    version="1.0.0",
)

origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrollment.router)
app.include_router(students.router)
app.include_router(attendance.router)


@app.on_event("startup")
async def startup_event():
    supabase = get_supabase_service()
    supabase.initialize()

    detector = get_detector()
    detector.initialize()
    detector.initialize_recognizer()

    print("Backend initialized")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    supabase = get_supabase_service()
    detector = get_detector()

    return HealthResponse(
        status="ok",
        supabase_connected=supabase.is_initialized(),
        models_loaded=detector.detector is not None,
    )


@app.get("/")
async def root():
    return {"name": "MARK Attendance API", "version": "1.0.0", "docs": "/docs"}
