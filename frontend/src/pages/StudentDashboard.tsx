import { useEffect, useState } from 'react'
import './StudentDashboard.css'
import { FaceRegistrationModal } from '../components/FaceRegistrationModal'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface Course {
  id: string
  name: string
  description: string | null
  created_at: string
}

interface Enrollment {
  course_id: string
}

interface StudentDashboardProps {
  user: User
}

export function StudentDashboard({ user }: StudentDashboardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [studentName, setStudentName] = useState<string | null>(null)
  const [courses, setCourses] = useState<Course[]>([])
  const [enrolledCourseIds, setEnrolledCourseIds] = useState<Set<string>>(new Set())
  const [loadingCourses, setLoadingCourses] = useState(true)
  const [enrollingCourseId, setEnrollingCourseId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoadingCourses(true)
      setError(null)

      try {
        const [
          { data: profile, error: profileError },
          { data: coursesData, error: coursesError },
          { data: enrollmentsData, error: enrollmentsError },
        ] = await Promise.all([
          supabase.from('profiles').select('name').eq('id', user.id).single(),
          supabase
            .from('courses')
            .select('id, name, description, created_at')
            .order('created_at', { ascending: false }),
          supabase
            .from('course_enrollments')
            .select('course_id')
            .eq('user_id', user.id),
        ])

        if (profileError) throw profileError
        if (coursesError) throw coursesError
        if (enrollmentsError) throw enrollmentsError

        setStudentName(profile?.name ?? null)
        setCourses(coursesData || [])
        setEnrolledCourseIds(
          new Set((enrollmentsData || []).map((enrollment: Enrollment) => enrollment.course_id))
        )
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      } finally {
        setLoadingCourses(false)
      }
    }

    fetchDashboardData()
  }, [user.id])

  const handleEnroll = async (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) return

    setEnrollingCourseId(courseId)
    setError(null)
    setSuccess(null)

    try {
      const { error: insertError } = await supabase
        .from('course_enrollments')
        .insert({
          course_id: courseId,
          user_id: user.id,
          status: 'active',
        })

      if (insertError) {
        const isDuplicate = insertError.message.toLowerCase().includes('duplicate')
        if (!isDuplicate) throw insertError
      }

      setEnrolledCourseIds(prev => new Set(prev).add(courseId))
      setSuccess('Enrolled successfully!')
      window.setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enroll')
    } finally {
      setEnrollingCourseId(null)
    }
  }

  const handleUnenroll = async (courseId: string) => {
    if (!window.confirm('Are you sure you want to unenroll from this course?')) return

    setEnrollingCourseId(courseId)
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
      window.setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unenroll')
    } finally {
      setEnrollingCourseId(null)
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
        Welcome{studentName ? `, ${studentName}` : ''}!
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <section className="courses-section">
        <h2 className="section-title">Available Courses</h2>

        {loadingCourses ? (
          <p className="loading-text">Loading courses...</p>
        ) : courses.length === 0 ? (
          <p className="empty-text">No courses available yet.</p>
        ) : (
          <div className="courses-grid">
            {courses.map(course => {
              const isEnrolled = enrolledCourseIds.has(course.id)
              const isProcessing = enrollingCourseId === course.id

              return (
                <div
                  key={course.id}
                  className={`course-card ${isEnrolled ? 'enrolled' : ''}`}
                >
                  <h3 className="course-name">{course.name}</h3>
                  {course.description ? (
                    <p className="course-description">{course.description}</p>
                  ) : (
                    <p className="course-description muted">No description provided.</p>
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
