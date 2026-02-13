import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
  headerAction?: React.ReactNode
}

export function Layout({ children, headerAction }: LayoutProps) {
  const navigate = useNavigate()

  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/')
  }

  return (
    <div className="layout">
      <header className="layout-header">
        <div className="logo">MARK</div>
        <div className="header-actions">
          {headerAction}
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>
      <main className="layout-main">
        {children}
      </main>
    </div>
  )
}
