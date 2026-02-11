import { useState } from 'react'
import { supabase, type UserRole } from '../lib/supabase'
import './LoginModal.css'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
}

export function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const [step, setStep] = useState<'select' | 'form'>('select')
  const [role, setRole] = useState<UserRole | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleRoleSelect = (selectedRole: UserRole) => {
    setRole(selectedRole)
    setStep('form')
    setError(null)
  }

  const handleBack = () => {
    setStep('select')
    setRole(null)
    setError(null)
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (signInError) throw signInError

      if (data.user) {
        const { data: profile } = await supabase
          .from('profiles')
          .select('role')
          .eq('id', data.user.id)
          .single()

        if (profile && profile.role !== role) {
          await supabase.auth.signOut()
          throw new Error(`This account is registered as a ${profile.role}, not a ${role}`)
        }

        onClose()
        window.location.href = role === 'teacher' ? '/teacher-dashboard' : '/student-dashboard'
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            role: role,
          },
        },
      })

      if (signUpError) throw signUpError

      if (data.user) {
        await supabase.from('profiles').insert([
          {
            id: data.user.id,
            email: data.user.email,
            role: role,
          },
        ])

        setError('Check your email to confirm your account!')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign up failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        
        {step === 'select' ? (
          <div className="role-selection">
            <h2>Login As</h2>
            <p className="role-subtitle">Select your account type</p>
            <div className="role-options">
              <button 
                className="role-btn teacher"
                onClick={() => handleRoleSelect('teacher')}
              >
                <span className="role-icon">👨‍🏫</span>
                <span className="role-label">Teacher</span>
                <span className="role-desc">Manage classes & attendance</span>
              </button>
              <button 
                className="role-btn student"
                onClick={() => handleRoleSelect('student')}
              >
                <span className="role-icon">👨‍🎓</span>
                <span className="role-label">Student</span>
                <span className="role-desc">View your attendance</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="login-form-container">
            <button className="back-btn" onClick={handleBack}>← Back</button>
            <h2>Login as {role}</h2>
            
            {error && (
              <div className={`alert ${error.includes('Check your email') ? 'alert-success' : 'alert-error'}`}>
                {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@school.edu"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              <button 
                type="submit" 
                className="login-submit-btn"
                disabled={loading}
              >
                {loading ? 'Loading...' : 'Login'}
              </button>
            </form>

            <div className="signup-section">
              <p>Don't have an account?</p>
              <button 
                className="signup-btn"
                onClick={handleSignUp}
                disabled={loading}
              >
                Sign Up as {role}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
