# MARK — Face Recognition Attendance System

AI-powered attendance system that uses facial recognition to automatically mark student attendance from classroom videos.

---

## How It Works

1. **Students** sign up and register their face by taking 3 photos
2. **Teachers** create courses and enroll students
3. **Teacher records** a short classroom video and uploads it
4. **AI processes** every frame — detects faces (YuNet) and matches them against enrolled students (SFace)
5. **Results** show who's present/absent with confidence scores

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, TypeScript, Vite |
| Backend | FastAPI, Python 3.10+ |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| Storage | Supabase Storage |
| Face Detection | OpenCV YuNet |
| Face Recognition | OpenCV SFace |

---

## Frontend

React + TypeScript SPA built with Vite.

- **Auth** — Login/Signup via Supabase Auth (email + password)
- **Student Dashboard** — Register face, view enrollment status
- **Teacher Dashboard** — Create courses, enroll students, upload attendance videos, view results
- **Settings** — Configure backend API URL

### Key Files

```
frontend/src/
├── pages/
│   ├── Login.tsx
│   ├── Signup.tsx
│   ├── StudentDashboard.tsx
│   ├── TeacherDashboard.tsx
│   └── Settings.tsx
├── components/          # Reusable UI components
├── lib/
│   ├── supabase.ts      # Supabase client
│   └── api.ts           # Backend API client + types
└── App.tsx              # Router + auth guard
```

The frontend connects to Supabase directly for **auth** and to the FastAPI backend for **face enrollment & attendance processing**.

---

## Backend

FastAPI server that handles face detection, recognition, and video processing.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/enrollment/check` | POST | Check if student ID/name already registered |
| `/api/enrollment/register` | POST | Register face with 3 photos |
| `/api/students` | GET | List enrolled students |
| `/api/students/{id}` | DELETE | Delete student enrollment |
| `/api/attendance/process` | POST | Process attendance from video |
| `/api/attendance/session/{id}` | GET | Get session results |
| `/api/attendance/history` | GET | Get attendance history |

### Key Files

```
backend/app/
├── main.py                  # FastAPI app + CORS + startup
├── config.py                # Settings from .env
├── routers/
│   ├── enrollment.py        # Face registration endpoints
│   ├── attendance.py        # Video processing endpoints
│   └── students.py          # Student CRUD endpoints
├── services/
│   ├── supabase_service.py  # All database operations
│   └── detector.py          # YuNet + SFace face AI
└── models/
    └── schemas.py           # Pydantic request/response models
```

---

## Database (Supabase)

PostgreSQL hosted on Supabase. The full schema is in [`schema.sql`](schema.sql).

### Tables

| Table | Purpose |
|-------|---------|
| `profiles` | User accounts — name, email, role, face embeddings (for students) |
| `courses` | Courses created by teachers |
| `course_enrollments` | Maps students to courses (many-to-many) |
| `attendance_sessions` | One row per processed video — totals, processing time |
| `attendance_records` | One row per student per session — present/absent, confidence |

### Key Design Decisions

- **`profiles`** merges identity + face data into one table. Teachers leave face fields `NULL`.
- **`course_enrollments`** has a composite `UNIQUE(course_id, user_id)` so students can join multiple courses.
- A **trigger** auto-creates a `profiles` row when a user signs up via Supabase Auth.
- The backend uses the **service key** (bypasses RLS) for all database operations.

### Storage

- **Bucket:** `enrollment-photos` (public) — stores the 3 face registration photos per student.

---

## How to Run

Frontend is hosted on **GitHub Pages**. You only need to run the backend locally and expose it via Cloudflare Tunnel.

**Terminal 1 — Start Backend:**
```bash
cd backend
source .venv/bin/activate
python run.py
```

**Terminal 2 — Start Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```
Copy the tunnel URL shown (e.g. `https://xxx-yyy.trycloudflare.com`)

**Connect Frontend to Backend:**
1. Open the app → go to **Settings** page
2. Paste the tunnel URL
3. Click **Save** → Refresh the page

> The tunnel URL changes every restart — just update it in Settings each time.

---

## License

MIT License
