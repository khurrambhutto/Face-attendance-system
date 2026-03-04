import { useEffect, useState } from 'react'
import './StudentDashboard.css'
import { FaceRegistrationModal } from '../components/FaceRegistrationModal'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface StudentDashboardProps {
  user: User
}

export function StudentDashboard({ user }: StudentDashboardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [studentName, setStudentName] = useState<string | null>(null)

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
      <p className="coming-soon">Course enrollment feature coming soon...</p>

      <FaceRegistrationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        userId={user.id}
      />
    </div>
  )
}
