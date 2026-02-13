import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setApiBaseUrl, clearApiBaseUrl, getDefaultApiUrl, getApiBaseUrl } from '../lib/api'
import './Settings.css'

export function Settings() {
  const navigate = useNavigate()
  const [apiUrl, setApiUrl] = useState('')
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'connected' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const currentUrl = getApiBaseUrl()
    setApiUrl(currentUrl)
  }, [])

  const handleTestConnection = async () => {
    if (!apiUrl.trim()) {
      setMessage('Please enter an API URL')
      return
    }

    setConnectionStatus('testing')
    setMessage('')

    const originalUrl = getApiBaseUrl()
    setApiBaseUrl(apiUrl.trim())
    
    const response = await api.health()
    
    if (response.data && response.data.status === 'ok') {
      setConnectionStatus('connected')
      setMessage(`Connected! Supabase: ${response.data.supabase_connected ? '✓' : '✗'}, Models: ${response.data.models_loaded ? '✓' : '✗'}`)
    } else {
      setConnectionStatus('error')
      setMessage(response.error || 'Connection failed')
      setApiBaseUrl(originalUrl)
    }
  }

  const handleSave = () => {
    if (!apiUrl.trim()) {
      setMessage('Please enter an API URL')
      return
    }

    setApiBaseUrl(apiUrl.trim())
    setSaved(true)
    setMessage('Settings saved! Refresh the page to apply changes.')
    
    setTimeout(() => {
      setSaved(false)
    }, 3000)
  }

  const handleReset = () => {
    const defaultUrl = getDefaultApiUrl()
    setApiUrl(defaultUrl)
    clearApiBaseUrl()
    setMessage('Reset to default URL. Click Save to apply.')
    setConnectionStatus('idle')
  }

  const handleBack = () => {
    navigate(-1)
  }

  return (
    <div className="settings-page">
      <div className="settings-container">
        <h1>Backend Settings</h1>
        <p className="settings-description">
          Configure the backend API URL. This is used when the cloudflare tunnel URL changes.
        </p>

        <div className="form-group">
          <label htmlFor="apiUrl">Backend API URL</label>
          <input
            id="apiUrl"
            type="url"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="https://your-tunnel.trycloudflare.com"
          />
          <span className="hint">Enter your cloudflare tunnel URL without trailing slash</span>
        </div>

        <div className="connection-status">
          <span className={`status-dot ${connectionStatus}`}></span>
          <span className="status-text">
            {connectionStatus === 'idle' && 'Not tested'}
            {connectionStatus === 'testing' && 'Testing...'}
            {connectionStatus === 'connected' && 'Connected'}
            {connectionStatus === 'error' && 'Connection failed'}
          </span>
        </div>

        {message && (
          <div className={`message ${connectionStatus === 'error' ? 'error' : 'info'}`}>
            {message}
          </div>
        )}

        <div className="button-group">
          <button className="btn-secondary" onClick={handleBack}>
            Back
          </button>
          <button className="btn-secondary" onClick={handleTestConnection} disabled={connectionStatus === 'testing'}>
            Test Connection
          </button>
          <button className="btn-secondary" onClick={handleReset}>
            Reset
          </button>
          <button className={`btn-primary ${saved ? 'saved' : ''}`} onClick={handleSave}>
            {saved ? 'Saved!' : 'Save'}
          </button>
        </div>

        <div className="settings-info">
          <h3>Instructions</h3>
          <ol>
            <li>Start your backend: <code>cd backend && uv run run.py</code></li>
            <li>Start cloudflare tunnel: <code>cloudflared tunnel --url http://localhost:8000</code></li>
            <li>Copy the tunnel URL from cloudflare output</li>
            <li>Paste the URL above and click Save</li>
            <li>Refresh the page to apply changes</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
