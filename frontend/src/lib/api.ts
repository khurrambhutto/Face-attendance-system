// ── API URL Management ──

const API_URL_KEY = 'mark_api_base_url'

export function getDefaultApiUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
}

export function getApiBaseUrl(): string {
  return localStorage.getItem(API_URL_KEY) || getDefaultApiUrl()
}

export function setApiBaseUrl(url: string): void {
  localStorage.setItem(API_URL_KEY, url)
}

export function clearApiBaseUrl(): void {
  localStorage.removeItem(API_URL_KEY)
}

/**
 * Check URL params for ?api=<url> and persist it.
 * Called once at app startup.
 */
export function initApiUrlFromParams(): void {
  const params = new URLSearchParams(window.location.search)
  const apiParam = params.get('api')
  if (apiParam) {
    setApiBaseUrl(apiParam)
  }
}

// ── Types ──

export interface HealthData {
  status: string
  supabase_connected: boolean
  models_loaded: boolean
}

export interface AttendanceSession {
  id: string
  course_id: string
  teacher_id: string
  video_filename: string | null
  total_frames: number
  total_students_present: number
  total_students_absent: number
  processing_time_seconds: number | null
  processed_at: string
  notes: string | null
}

export interface AttendanceRecord {
  id: string
  session_id: string
  user_id: string | null
  student_name: string
  student_id: string
  is_present: boolean
  confidence_score: number | null
  frames_detected: number
  frames_total: number
  best_frame_path: string | null
}

export interface AttendanceSessionDetail {
  session: AttendanceSession
  records: AttendanceRecord[]
}

export interface ProcessAttendanceData {
  job_id: string
  message: string
}

export interface ProcessingProgress {
  job_id: string
  status: 'processing' | 'completed' | 'error'
  progress: number
  session_id: string | null
  total_students_present: number | null
  total_students_absent: number | null
  error: string | null
}

export interface CheckEnrollmentData {
  exists: boolean
  duplicate_id: boolean
  duplicate_name: boolean
  message: string
}

export interface RegisterEnrollmentData {
  success: boolean
  enrollment_id: string | null
  message: string
}

interface ApiResponse<T> {
  data: T | null
  error: string | null
}

// ── API Client ──

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const base = getApiBaseUrl()
  try {
    const res = await fetch(`${base}${path}`, options)
    if (!res.ok) {
      const body = await res.json().catch(() => null)
      return { data: null, error: body?.detail || `HTTP ${res.status}` }
    }
    const data = await res.json()
    return { data, error: null }
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : 'Network error' }
  }
}

export const api = {
  health(): Promise<ApiResponse<HealthData>> {
    return request<HealthData>('/health')
  },

  checkEnrollment(studentId: string, studentName: string): Promise<ApiResponse<CheckEnrollmentData>> {
    return request<CheckEnrollmentData>('/api/enrollment/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, student_name: studentName }),
    })
  },

  registerEnrollment(
    userId: string,
    studentId: string,
    studentName: string,
    photos: Blob[]
  ): Promise<ApiResponse<RegisterEnrollmentData>> {
    const formData = new FormData()
    formData.append('user_id', userId)
    formData.append('student_id', studentId)
    formData.append('student_name', studentName)
    photos.forEach((photo, i) => {
      formData.append('photos', photo, `photo_${i}.jpg`)
    })
    return request<RegisterEnrollmentData>('/api/enrollment/register', {
      method: 'POST',
      body: formData,
    })
  },

  processAttendance(
    courseId: string,
    teacherId: string,
    video: File
  ): Promise<ApiResponse<ProcessAttendanceData>> {
    const formData = new FormData()
    formData.append('course_id', courseId)
    formData.append('teacher_id', teacherId)
    formData.append('video', video)
    return request<ProcessAttendanceData>('/api/attendance/process', {
      method: 'POST',
      body: formData,
    })
  },

  getProcessingProgress(jobId: string): Promise<ApiResponse<ProcessingProgress>> {
    return request<ProcessingProgress>(`/api/attendance/progress/${jobId}`)
  },

  getAttendanceSession(sessionId: string): Promise<ApiResponse<AttendanceSessionDetail>> {
    return request<AttendanceSessionDetail>(`/api/attendance/session/${sessionId}`)
  },

  getAttendanceHistory(
    courseId?: string,
    teacherId?: string,
    limit = 20,
    offset = 0
  ): Promise<ApiResponse<{ sessions: AttendanceSession[]; total: number }>> {
    const params = new URLSearchParams()
    if (courseId) params.set('course_id', courseId)
    if (teacherId) params.set('teacher_id', teacherId)
    params.set('limit', String(limit))
    params.set('offset', String(offset))
    return request(`/api/attendance/history?${params}`)
  },
}
