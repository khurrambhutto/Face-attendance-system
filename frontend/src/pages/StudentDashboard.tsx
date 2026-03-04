import { useEffect, useState } from 'react'
import './StudentDashboard.css'
import { FaceRegistrationModal } from '../components/FaceRegistrationModal'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface StudentDashboardProps {
  user: User
}

interface Course {
  id: string
  name: string
  description: string | null
  created_at: string
}

export function StudentDashboard({ user }: StudentDashboardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [studentName, setStudentName] = useState<string | null>(null)
  const [courses, setCourses] = useState<Course[]>([])
  const [enrolledCourseIds, setEnrolledCourseIds] = useState<Set<string>>(new Set())
  const [loadingCourses, setLoadingCourses] = useState(false)
  const [enrollingCourseId, setEnrollingCourseId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const fetchStudentName = async () => {
      const { data } = await supabase
        .from('profiles')
        .select('name')
        .eq('id', user.id)
        .single()

      if (data?.name) {
        setStudentName(data.name)
      }
    }

    fetchStudentName()
  }, [user.id])

  useEffect(() => {
    fetchCoursesAndEnrollments()
  }, [user.id])

  const fetchCoursesAndEnrollments = async () => {
    setLoadingCourses(true)
    setError(null)
    try {
      const [{ data: coursesData, error: coursesError }, { data: enrollmentsData, error: enrollmentsError }] = await Promise.all([
        supabase
          .from('courses')
          .select('id, name, description, created_at')
          .order('created_at', { ascending: false }),
        supabase
          .from('course_enrollments')
          .select('course_id')
          .eq('user_id', user.id),
      ])

      if (coursesError) throw coursesError
      if (enrollmentsError) throw enrollmentsError

      setCourses(coursesData || [])
      setEnrolledCourseIds(new Set((enrollmentsData || []).map((enrollment) => enrollment.course_id)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load courses')
    } finally {
      setLoadingCourses(false)
    }
  }

  const handleEnroll = async (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) return

    setEnrollingCourseId(courseId)
    setError(null)
    setSuccess(null)

    try {
      const { error: insertError } = await supabase.from('course_enrollments').insert({
        course_id: courseId,
        user_id: user.id,
        status: 'active',
      })

      if (insertError) {
        const isDuplicate = insertError.message.toLowerCase().includes('duplicate')
        if (!isDuplicate) throw insertError
      }

      setEnrolledCourseIds((prev) => new Set(prev).add(courseId))
      setSuccess('Enrolled successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enroll in course')
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

      <section className="courses-section">
        <h2 className="section-title">Available Courses</h2>
        {loadingCourses ? (
          <div className="loading">Loading courses...</div>
        ) : courses.length === 0 ? (
          <div className="empty-state">No courses available yet.</div>
        ) : (
          <div className="courses-grid">
            {courses.map((course) => {
              const isEnrolled = enrolledCourseIds.has(course.id)
              return (
                <div key={course.id} className="course-card">
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
                    <button
                      className="enroll-btn"
                      disabled={isEnrolled || enrollingCourseId === course.id}
                      onClick={() => handleEnroll(course.id)}
                    >
                      {isEnrolled ? 'Enrolled' : (enrollingCourseId === course.id ? 'Enrolling...' : 'Enroll')}
                    </button>
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
