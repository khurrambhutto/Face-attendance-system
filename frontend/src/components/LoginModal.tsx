import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase, type UserRole } from '../lib/supabase'
import './LoginModal.css'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'login' | 'signup'
}

export function LoginModal({ isOpen, onClose, initialMode = 'login' }: LoginModalProps) {
  const navigate = useNavigate()
  const [step, setStep] = useState<'select' | 'form'>('select')
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode)
  const [role, setRole] = useState<UserRole | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state when modal opens or mode changes
  useEffect(() => {
    if (isOpen) {
      setStep('select')
      setMode(initialMode)
      setRole(null)
      setName('')
      setEmail('')
      setPassword('')
      setError(null)
    }
  }, [isOpen, initialMode])

  if (!isOpen) return null

  const handleRoleSelect = (selectedRole: UserRole) => {
    setRole(selectedRole)
    setStep('form')
    setMode(initialMode)
    setError(null)
  }

  const handleBack = () => {
    setStep('select')
    setRole(null)
    setName('')
    setError(null)
  }

  const handleSwitchMode = (newMode: 'login' | 'signup') => {
    setMode(newMode)
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
        const { data: profiles } = await supabase
          .from('profiles')
          .select('role')
          .eq('id', data.user.id)

        const profile = profiles?.[0]
        if (profile && profile.role !== role) {
          await supabase.auth.signOut()
          throw new Error(`This account is registered as a ${profile.role}, not a ${role}`)
        }

        onClose()
        navigate(role === 'teacher' ? '/teacher-dashboard' : '/student-dashboard')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return
    if (!name.trim()) {
      setError('Name is required')
      return
    }
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
        // Trigger already created the profile row, so we UPDATE it
        await supabase.from('profiles')
          .update({
            name: name.trim(),
            role: role,
          })
          .eq('id', data.user.id)

        // Auto-login and redirect
        onClose()
        navigate(role === 'teacher' ? '/teacher-dashboard' : '/student-dashboard')
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
            <h2>{initialMode === 'signup' ? 'Sign Up As' : 'Login As'}</h2>
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
            <h2>{mode === 'login' ? 'Login' : 'Sign Up'} as {role}</h2>

            {error && (
              <div className={`alert ${error.includes('Check your email') ? 'alert-success' : 'alert-error'}`}>
                {error}
              </div>
            )}

            <form onSubmit={mode === 'login' ? handleLogin : handleSignUp} className="login-form">
              {mode === 'signup' && (
                <div className="form-group">
                  <label htmlFor="name">Full Name *</label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="John Doe"
                    required
                  />
                </div>
              )}

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
                {loading ? 'Loading...' : (mode === 'login' ? 'Login' : 'Sign Up')}
              </button>
            </form>

            <div className="mode-toggle">
              {mode === 'login' ? (
                <p>Don't have an account? <button onClick={() => handleSwitchMode('signup')}>Sign Up</button></p>
              ) : (
                <p>Already have an account? <button onClick={() => handleSwitchMode('login')}>Login</button></p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
