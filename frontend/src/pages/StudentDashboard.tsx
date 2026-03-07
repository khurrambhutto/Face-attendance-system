import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import './StudentDashboard.css'
import { FaceRegistrationModal } from '../components/FaceRegistrationModal'
import type { User } from '@supabase/supabase-js'

interface Course {
  id: string
  name: string
  description: string | null
  created_at: string
  teacher_id: string
}

interface Enrollment {
  course_id: string
}

interface StudentDashboardProps {
  user: User
}

export function StudentDashboard({ user }: StudentDashboardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [courses, setCourses] = useState<Course[]>([])
  const [enrolledCourseIds, setEnrolledCourseIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [enrolling, setEnrolling] = useState<string | null>(null)
  const [userName, setUserName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch user profile for name
      const { data: profile } = await supabase
        .from('profiles')
        .select('name')
        .eq('id', user.id)
        .single()

      if (profile?.name) {
        setUserName(profile.name)
      }

      // Fetch all courses
      const { data: allCourses, error: coursesError } = await supabase
        .from('courses')
        .select('*')
        .order('created_at', { ascending: false })

      if (coursesError) throw coursesError
      setCourses(allCourses || [])

      // Fetch this student's enrollments
      const { data: enrollments, error: enrollError } = await supabase
        .from('course_enrollments')
        .select('course_id')
        .eq('user_id', user.id)

      if (enrollError) throw enrollError

      const enrolledIds = new Set<string>(
        (enrollments || []).map((e: Enrollment) => e.course_id)
      )
      setEnrolledCourseIds(enrolledIds)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleEnroll = async (courseId: string) => {
    setEnrolling(courseId)
    setError(null)
    setSuccess(null)

    try {
      const { error: enrollError } = await supabase
        .from('course_enrollments')
        .insert({
          course_id: courseId,
          user_id: user.id,
          status: 'active',
        })

      if (enrollError) throw enrollError

      setEnrolledCourseIds(prev => new Set(prev).add(courseId))
      setSuccess('Enrolled successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enroll')
    } finally {
      setEnrolling(null)
    }
  }

  const handleUnenroll = async (courseId: string) => {
    if (!confirm('Are you sure you want to unenroll from this course?')) return

    setEnrolling(courseId)
    setError(null)

    try {
      const { error: unenrollError } = await supabase
        .from('course_enrollments')
        .delete()
        .eq('course_id', courseId)
        .eq('user_id', user.id)

      if (unenrollError) throw unenrollError

      setEnrolledCourseIds(prev => {
        const next = new Set(prev)
        next.delete(courseId)
        return next
      })
      setSuccess('Unenrolled successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unenroll')
    } finally {
      setEnrolling(null)
    }
  }

  return (
    <div className="student-dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">My Dashboard</h1>
        <button
          className="register-face-btn"
          onClick={() => setIsModalOpen(true)}
        >
          Register Face
        </button>
      </div>

      <p className="welcome-message">
        Welcome{userName ? `, ${userName}` : ''}!
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <section className="courses-section">
        <h2 className="section-title">Available Courses</h2>

        {loading ? (
          <p className="loading-text">Loading courses...</p>
        ) : courses.length === 0 ? (
          <p className="empty-text">No courses available yet.</p>
        ) : (
          <div className="courses-grid">
            {courses.map(course => {
              const isEnrolled = enrolledCourseIds.has(course.id)
              const isProcessing = enrolling === course.id

              return (
                <div key={course.id} className={`course-card ${isEnrolled ? 'enrolled' : ''}`}>
                  <h3 className="course-name">{course.name}</h3>
                  {course.description && (
                    <p className="course-description">{course.description}</p>
                  )}
                  <div className="course-footer">
                    <span className="course-date">
                      Created: {new Date(course.created_at).toLocaleDateString()}
                    </span>
                    {isEnrolled ? (
                      <button
                        className="enroll-btn enrolled-badge"
                        onClick={() => handleUnenroll(course.id)}
                        disabled={isProcessing}
                      >
                        {isProcessing ? '...' : 'Enrolled'}
                      </button>
                    ) : (
                      <button
                        className="enroll-btn"
                        onClick={() => handleEnroll(course.id)}
                        disabled={isProcessing}
                      >
                        {isProcessing ? 'Enrolling...' : 'Enroll'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <FaceRegistrationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        userId={user.id}
      />
    </div>
  )
}
