import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import type { User } from '@supabase/supabase-js'
import { AttendanceModal } from '../components/AttendanceModal'
import './TeacherDashboard.css'

interface Course {
  id: string
  name: string
  description: string | null
  created_at: string
  teacher_id: string
  course_enrollments?: Enrollment[]
}

interface Enrollment {
  id: string
  course_id: string
  user_id: string
  enrolled_at: string
  status: string
  profiles?: { email: string | null }
}

interface TeacherDashboardProps {
  user: User
}

export function TeacherDashboard({ user }: TeacherDashboardProps) {
  const [courses, setCourses] = useState<Course[]>([])
  const [courseName, setCourseName] = useState('')
  const [courseDescription, setCourseDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [expandedCourses, setExpandedCourses] = useState<Set<string>>(new Set())
  const [attendanceModalOpen, setAttendanceModalOpen] = useState(false)
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null)

  useEffect(() => {
    fetchCourses()
  }, [])

  const fetchCourses = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error } = await supabase
        .from('courses')
        .select(`
          *,
          course_enrollments(
            enrolled_at,
            status,
            user_id
          )
        `)
        .eq('teacher_id', user.id)
        .order('created_at', { ascending: false })

      if (error) throw error
      setCourses(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch courses')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseName.trim()) {
      setError('Course name is required')
      return
    }

    setCreating(true)
    setError(null)
    setSuccess(null)

    try {
      const { error } = await supabase.from('courses').insert({
        name: courseName.trim(),
        description: courseDescription.trim() || null,
        teacher_id: user.id,
      })

      if (error) throw error

      setSuccess('Course created successfully!')
      setCourseName('')
      setCourseDescription('')
      await fetchCourses()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create course')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteCourse = async (courseId: string) => {
    if (!confirm('Are you sure you want to delete this course?')) return

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const { error } = await supabase
        .from('courses')
        .delete()
        .eq('id', courseId)
        .eq('teacher_id', user.id)

      if (error) throw error

      setSuccess('Course deleted successfully!')
      await fetchCourses()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete course')
    } finally {
      setLoading(false)
    }
  }

  const toggleExpandCourse = (courseId: string) => {
    setExpandedCourses((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(courseId)) {
        newSet.delete(courseId)
      } else {
        newSet.add(courseId)
      }
      return newSet
    })
  }

  const openAttendanceModal = (courseId: string) => {
    setSelectedCourseId(courseId)
    setAttendanceModalOpen(true)
  }

  const closeAttendanceModal = () => {
    setAttendanceModalOpen(false)
    setSelectedCourseId(null)
  }

  return (
    <div className="teacher-dashboard">
      <h1 className="dashboard-title">My Courses</h1>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          {success}
        </div>
      )}

      <section className="create-course-section">
        <h2 className="section-title">Create New Course</h2>
        <form onSubmit={handleCreateCourse} className="create-course-form">
          <div className="form-group">
            <label htmlFor="courseName">Course Name *</label>
            <input
              id="courseName"
              type="text"
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
              placeholder="e.g., Computer Science 101"
              disabled={creating}
            />
          </div>
          <div className="form-group">
            <label htmlFor="courseDescription">Description</label>
            <textarea
              id="courseDescription"
              value={courseDescription}
              onChange={(e) => setCourseDescription(e.target.value)}
              placeholder="Optional description for students..."
              rows={3}
              disabled={creating}
            />
          </div>
          <button type="submit" className="create-course-btn" disabled={creating}>
            {creating ? 'Creating...' : 'Create Course'}
          </button>
        </form>
      </section>

      <section className="courses-section">
        <h2 className="section-title">My Courses</h2>
        {loading && !courses.length ? (
          <div className="loading">Loading courses...</div>
        ) : courses.length === 0 ? (
          <div className="empty-state">No courses yet. Create your first course above!</div>
        ) : (
          <div className="courses-grid">
            {courses.map((course) => (
              <div key={course.id} className="course-card">
                <div className="course-header">
                  <h3 className="course-name">{course.name}</h3>
                  <button
                    onClick={() => handleDeleteCourse(course.id)}
                    className="delete-btn"
                    title="Delete course"
                  >
                    ×
                  </button>
                </div>
                {course.description && (
                  <p className="course-description">{course.description}</p>
                )}
                <div className="course-meta">
                  <span className="course-date">
                    Created: {new Date(course.created_at).toLocaleDateString()}
                  </span>
                  <span className="course-enrollments-count">
                    {course.course_enrollments?.length || 0} students
                  </span>
                </div>

                <div className="course-actions">
                  <button
                    onClick={() => openAttendanceModal(course.id)}
                    className="attendance-btn"
                  >
                    Take Attendance
                  </button>
                  {(course.course_enrollments && course.course_enrollments.length > 0) && (
                    <button
                      onClick={() => toggleExpandCourse(course.id)}
                      className="toggle-students-btn"
                    >
                      {expandedCourses.has(course.id) ? 'Hide' : 'Students'}
                    </button>
                  )}
                </div>

                {expandedCourses.has(course.id) && course.course_enrollments && course.course_enrollments.length > 0 && (
                  <div className="enrolled-students">
                    <h4>Enrolled Students</h4>
                    <ul className="students-list">
                      {course.course_enrollments.map((enrollment) => (
                        <li key={enrollment.id} className="student-item">
                          <div className="student-info">
                            <span className="student-email">{enrollment.user_id}</span>
                            <span className="enrollment-date">
                              Enrolled: {new Date(enrollment.enrolled_at).toLocaleDateString()}
                            </span>
                          </div>
                          <span className={`status status-${enrollment.status}`}>
                            {enrollment.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedCourseId && (
        <AttendanceModal
          isOpen={attendanceModalOpen}
          onClose={closeAttendanceModal}
          courseId={selectedCourseId}
          teacherId={user.id}
        />
      )}
    </div>
  )
}
