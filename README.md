# MARK - Face Recognition Attendance System

AI-powered attendance system using facial recognition. Teachers can create courses, students can register their faces, and attendance is marked automatically from classroom videos.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌──────────────────────┐      ┌─────────────────────────────┐
│   GitHub Pages       │      │   Cloudflare Tunnel         │
│   (Frontend - React) │──────│   your-url.trycloudflare.com│
│   Static Hosting     │      │   → localhost:8000          │
└──────────────────────┘      └──────────────┬──────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │   YOUR PC (FastAPI:8000)     │
                              │   - YuNet/SFace ML models    │
                              │   - Video processing         │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │   Supabase (Cloud - Free)    │
                              │   - Auth (user accounts)     │
                              │   - Database (PostgreSQL)    │
                              │   - Storage (photos)         │
                              └──────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Supabase account (free at supabase.com)
- Cloudflared installed (`sudo snap install cloudflared`)

---

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/khurrambhutto/Face-attendance-system.git
cd Face-attendance-system
```

### 2. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a free project
2. Run the SQL below in Supabase SQL Editor:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table (user accounts)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    email TEXT,
    role TEXT CHECK (role IN ('student', 'teacher')),
    name TEXT
);

-- Courses table
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    teacher_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Face enrollments table
CREATE TABLE IF NOT EXISTS enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    student_id TEXT,
    student_name TEXT,
    photo_urls JSONB,
    embeddings JSONB,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'active'
);

-- Course enrollments (students in courses)
CREATE TABLE IF NOT EXISTS course_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    student_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active',
    user_id UUID REFERENCES profiles(id)
);

-- Attendance sessions table
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES profiles(id),
    video_filename TEXT,
    total_frames INTEGER DEFAULT 0,
    total_students_present INTEGER DEFAULT 0,
    total_students_absent INTEGER DEFAULT 0,
    processing_time_seconds FLOAT,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- Attendance records table
CREATE TABLE IF NOT EXISTS attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(id) ON DELETE SET NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    student_name TEXT NOT NULL,
    student_id TEXT NOT NULL,
    is_present BOOLEAN DEFAULT TRUE,
    confidence_score FLOAT,
    frames_detected INTEGER DEFAULT 0,
    frames_total INTEGER DEFAULT 0,
    best_frame_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
CREATE POLICY "Public profiles are viewable by everyone"
    ON profiles FOR SELECT USING (true);

CREATE POLICY "Users can insert their own profile"
    ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE USING (auth.uid() = id);

-- Create storage bucket for enrollment photos
INSERT INTO storage.buckets (id, name, public)
VALUES ('enrollment-photos', 'enrollment-photos', true)
ON CONFLICT (id) DO NOTHING;
```

3. Get your API keys from Project Settings → API:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY` (service_role key - keep secret!)

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

Edit `backend/.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_BUCKET=enrollment-photos

LOCAL_VIDEOS_PATH=./local_data/videos
LOCAL_FRAMES_PATH=./local_data/frames

CORS_ORIGINS=*
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

Edit `frontend/.env`:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_BASE_PATH=/Face-attendance-system/
VITE_API_BASE_URL=http://localhost:8000
```

---

## Running the Application

### Development (Local)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uv run run.py
```
Backend runs at: `http://localhost:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Frontend runs at: `http://localhost:5173`

---

### Production (GitHub Pages + Cloudflare Tunnel)

**Step 1: Deploy Frontend to GitHub Pages**

```bash
cd frontend
npm run deploy
```

This builds and pushes to the `gh-pages` branch.

Your app will be at: `https://yourusername.github.io/Face-attendance-system/`

**Step 2: Start Backend**

```bash
cd backend
source venv/bin/activate
uv run run.py
```

**Step 3: Start Cloudflare Tunnel**

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the tunnel URL shown (e.g., `https://xxx-yyy.trycloudflare.com`)

**Step 4: Update API URL**

1. Go to: `https://yourusername.github.io/Face-attendance-system/#/settings`
2. Paste the tunnel URL
3. Click "Test Connection" to verify
4. Click "Save"
5. Refresh the page

---

## Usage Guide

### For Teachers

1. **Login** as Teacher
2. **Create Course** - Enter course name and description
3. **Share Course** - Students can enroll using course ID
4. **Take Attendance** - Click "Take Attendance" on a course card
5. **Upload Video** - Record 10-30 seconds of classroom, slowly panning
6. **View Results** - See present/absent students with confidence scores

### For Students

1. **Login** as Student
2. **Register Face** - Click "Register Face" button
3. **Enter Details** - Student ID and name
4. **Capture Photos** - Take 3 clear photos of your face
5. **Save** - Face is now registered for attendance

---

## Quick Reference

### URLs

| Environment | Frontend | Backend |
|-------------|----------|---------|
| Development | `http://localhost:5173` | `http://localhost:8000` |
| Production | `https://yourusername.github.io/Face-attendance-system/` | Cloudflare tunnel URL |

### Settings Page

When tunnel URL changes:
1. Open: `https://yourusername.github.io/Face-attendance-system/#/settings`
2. Update URL → Save → Refresh

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | - | Health check |
| `POST /api/enrollment/check` | - | Check duplicate enrollment |
| `POST /api/enrollment/register` | - | Register face with photos |
| `GET /api/students` | - | List enrolled students |
| `DELETE /api/students/{id}` | - | Delete student enrollment |
| `POST /api/attendance/process` | - | Process attendance video |
| `GET /api/attendance/session/{id}` | - | Get session results |
| `GET /api/attendance/history` | - | Get attendance history |

---

## Project Structure

```
Face-attendance-system/
├── frontend/                    # React + Vite
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/              # Page components
│   │   │   ├── Settings.tsx    # Backend URL config
│   │   │   ├── TeacherDashboard.tsx
│   │   │   └── StudentDashboard.tsx
│   │   ├── lib/
│   │   │   ├── api.ts          # Backend API client
│   │   │   └── supabase.ts     # Supabase client
│   │   └── main.tsx
│   ├── .env
│   └── vite.config.ts
│
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # Settings
│   │   ├── routers/
│   │   │   ├── enrollment.py   # Face enrollment API
│   │   │   ├── attendance.py   # Attendance processing
│   │   │   └── students.py     # Student management
│   │   ├── services/
│   │   │   ├── detector.py     # YuNet + SFace ML
│   │   │   └── supabase_service.py
│   │   └── models/
│   │       └── schemas.py      # Pydantic models
│   ├── local_data/             # Local storage
│   ├── .env
│   ├── requirements.txt
│   └── run.py
│
└── models/                      # ONNX models (auto-downloaded)
    ├── face_detection_yunet_2023mar.onnx
    └── face_recognition_sface_2021dec.onnx
```

---

## Troubleshooting

### "Failed to save enrollment to database"
- Check Supabase service key in `backend/.env`
- Ensure user has a profile in `profiles` table

### "No face detected in photo"
- Ensure good lighting
- Face the camera directly
- Move closer to camera

### "Connection failed" on Settings page
- Verify backend is running (`uv run run.py`)
- Verify tunnel is active (`cloudflared tunnel --url http://localhost:8000`)
- Update tunnel URL in Settings page

### "404 Not Found" on GitHub Pages
- Clear browser cache (Ctrl+Shift+R)
- Use hash routes: `/#/settings` not `/settings`

### Tunnel URL changes every restart
- This is normal for free cloudflare tunnels
- Update URL in Settings page after restart
- Or set up a named tunnel for permanent URL

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, Vite 7, TypeScript |
| Backend | FastAPI, Python 3.10+ |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| Storage | Supabase Storage |
| Face Detection | OpenCV YuNet |
| Face Recognition | OpenCV SFace |
| Deployment | GitHub Pages + Cloudflare Tunnel |

---

## License

MIT License
