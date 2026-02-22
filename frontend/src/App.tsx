import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { LoginModal } from './components/LoginModal'
import { Layout } from './components/Layout'
import { TeacherDashboard } from './pages/TeacherDashboard'
import { StudentDashboard } from './pages/StudentDashboard'
import { Settings } from './pages/Settings'
import { supabase } from './lib/supabase'
import type { User } from '@supabase/supabase-js'

function App() {
  const [isLoginOpen, setIsLoginOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [user, setUser] = useState<User | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }: { data: { session: { user: User | null } | null } }) => {
      setUser(session?.user ?? null)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: string, session: { user: User | null } | null) => {
      setUser(session?.user ?? null)
      if (!session?.user) setUserRole(null)
    })

    return () => subscription.unsubscribe()
  }, [])

  // Fetch user role when user changes
  useEffect(() => {
    if (user) {
      supabase.from('profiles').select('role').eq('id', user.id).then(({ data }) => {
        setUserRole(data?.[0]?.role ?? null)
      })
    }
  }, [user])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setUserRole(null)
  }

  return (
    <Routes>
      <Route path="/" element={
        user && userRole ? (
          <Navigate to={userRole === 'teacher' ? '/teacher-dashboard' : '/student-dashboard'} />
        ) : (
          <div className="app">
            <header className="header">
              <div className="logo">MARK</div>
              {user ? (
                <button onClick={handleLogout} className="login-link">Logout</button>
              ) : (
                <div className="auth-buttons">
                  <button onClick={() => { setAuthMode('login'); setIsLoginOpen(true) }} className="login-link">Login</button>
                  <button onClick={() => { setAuthMode('signup'); setIsLoginOpen(true) }} className="signup-link">Sign Up</button>
                </div>
              )}
            </header>

            <main className="main">
              <section className="hero">
                <h1>
                  ATTENDANCE
                  <span className="accent">MADE SIMPLE</span>
                </h1>
                <p>Record a 10-second classroom video. Our AI identifies every student and marks attendance automatically. No more roll calls.</p>
              </section>

              <section className="features">
                <div className="feature-card">
                  <div className="feature-number">01</div>
                  <h3 className="feature-title">Quick Capture</h3>
                  <p className="feature-desc">Record a brief 10-second video of your classroom using any device.</p>
                </div>
                <div className="feature-card">
                  <div className="feature-number">02</div>
                  <h3 className="feature-title">AI Detection</h3>
                  <p className="feature-desc">Advanced facial recognition instantly identifies each enrolled student.</p>
                </div>
                <div className="feature-card">
                  <div className="feature-number">03</div>
                  <h3 className="feature-title">Auto Marking</h3>
                  <p className="feature-desc">Attendance records generated and synced to your dashboard in seconds.</p>
                </div>
              </section>
            </main>

            <footer className="footer">
              <p>&copy; 2026 MARK</p>
              <div className="footer-links">
                <a href="#">Privacy</a>
                <a href="#">Terms</a>
                <a href="#">Contact</a>
              </div>
            </footer>

            <LoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} initialMode={authMode} />
          </div>
        )
      } />
      <Route path="/teacher-dashboard" element={
        user ? (
          <Layout>
            <TeacherDashboard user={user} />
          </Layout>
        ) : (
          <Navigate to="/" />
        )
      } />
      <Route path="/student-dashboard" element={
        user ? (
          <Layout>
            <StudentDashboard user={user} />
          </Layout>
        ) : (
          <Navigate to="/" />
        )
      } />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  )
}

export default App
