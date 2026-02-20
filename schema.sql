-- ============================================
-- MARK ATTENDANCE SYSTEM — CLEAN SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. PROFILES (merged with old enrollments table)
-- One row per user. Students get face data here too.
-- Teachers leave student-specific fields NULL.
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  name TEXT,
  role TEXT DEFAULT 'student',          -- 'student' | 'teacher'
  student_id TEXT UNIQUE,               -- roll number (NULL for teachers)
  embeddings JSONB,                     -- face embedding vectors (NULL for teachers)
  photo_urls JSONB,                     -- enrollment photo URLs (NULL for teachers)
  enrollment_status TEXT DEFAULT 'pending',  -- 'pending' | 'active' (face registration)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. COURSES
-- Created by teachers. Students enroll via course_enrollments.
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  teacher_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. COURSE ENROLLMENTS
-- Maps students to courses (many-to-many).
-- Composite UNIQUE ensures a student can't enroll in the same course twice,
-- but CAN enroll in multiple different courses.
CREATE TABLE course_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMPTZ DEFAULT now(),
  status TEXT DEFAULT 'active',
  UNIQUE(course_id, user_id)
);

-- 4. ATTENDANCE SESSIONS
-- One row per video processed by the AI.
-- Links to the course and teacher who submitted it.
CREATE TABLE attendance_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
  teacher_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  video_filename TEXT,
  total_frames INTEGER DEFAULT 0,
  total_students_present INTEGER DEFAULT 0,
  total_students_absent INTEGER DEFAULT 0,
  processing_time_seconds DOUBLE PRECISION,
  processed_at TIMESTAMPTZ DEFAULT now(),
  notes TEXT
);

-- 5. ATTENDANCE RECORDS
-- One row per student per session (present or absent).
-- Contains AI confidence data for recognized students.
CREATE TABLE attendance_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES attendance_sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  student_name TEXT NOT NULL,
  student_id TEXT NOT NULL,
  is_present BOOLEAN DEFAULT true,
  confidence_score DOUBLE PRECISION,
  frames_detected INTEGER DEFAULT 0,
  frames_total INTEGER DEFAULT 0,
  best_frame_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. AUTO-CREATE PROFILE ON SIGNUP
-- Trigger: when a new user signs up via Supabase Auth,
-- automatically create a profiles row with their email.
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- 7. BACKFILL EXISTING AUTH USERS
-- Creates profile rows for users who signed up before this schema existed.
INSERT INTO profiles (id, email)
SELECT id, email FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- 8. INDEXES FOR PERFORMANCE
CREATE INDEX idx_courses_teacher ON courses(teacher_id);
CREATE INDEX idx_course_enrollments_course ON course_enrollments(course_id);
CREATE INDEX idx_course_enrollments_user ON course_enrollments(user_id);
CREATE INDEX idx_attendance_sessions_course ON attendance_sessions(course_id);
CREATE INDEX idx_attendance_records_session ON attendance_records(session_id);
CREATE INDEX idx_profiles_role ON profiles(role);

-- ============================================
-- STORAGE: Also create a public bucket named
-- "enrollment-photos" in Supabase Dashboard
-- (Storage → New Bucket → enrollment-photos → Public)
-- ============================================
