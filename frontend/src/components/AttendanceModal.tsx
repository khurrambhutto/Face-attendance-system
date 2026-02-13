import { useState, useRef } from 'react'
import './AttendanceModal.css'
import { api, type AttendanceRecord, type AttendanceSession } from '../lib/api'

interface AttendanceModalProps {
  isOpen: boolean
  onClose: () => void
  courseId: string
  teacherId: string
}

type Step = 'upload' | 'processing' | 'results' | 'error'

export function AttendanceModal({ isOpen, onClose, courseId, teacherId }: AttendanceModalProps) {
  const [step, setStep] = useState<Step>('upload')
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [error, setError] = useState<string>('')
  const [session, setSession] = useState<AttendanceSession | null>(null)
  const [records, setRecords] = useState<AttendanceRecord[]>([])
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const validTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/quicktime', 'video/x-msvideo']
      if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
        setError('Please select a valid video file (MP4, AVI, MOV, MKV)')
        return
      }
      setVideoFile(file)
      setError('')
    }
  }

  const handleProcess = async () => {
    if (!videoFile) {
      setError('Please select a video file')
      return
    }

    setStep('processing')
    setError('')
    setProgress(0)

    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + 5, 90))
    }, 500)

    try {
      const response = await api.processAttendance(courseId, teacherId, videoFile)

      clearInterval(progressInterval)
      setProgress(100)

      if (response.error) {
        setError(response.error)
        setStep('error')
        return
      }

      if (response.data?.session_id) {
        const sessionResponse = await api.getAttendanceSession(response.data.session_id)
        
        if (sessionResponse.data) {
          setSession(sessionResponse.data.session)
          setRecords(sessionResponse.data.records)
          setStep('results')
        } else {
          setError('Failed to fetch attendance results')
          setStep('error')
        }
      } else {
        setError('No session ID returned')
        setStep('error')
      }
    } catch (err) {
      clearInterval(progressInterval)
      setError(err instanceof Error ? err.message : 'An error occurred')
      setStep('error')
    }
  }

  const reset = () => {
    setStep('upload')
    setVideoFile(null)
    setError('')
    setSession(null)
    setRecords([])
    setProgress(0)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}m ${secs}s`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  if (!isOpen) return null

  return (
    <div className="attendance-modal-overlay">
      <div className="attendance-modal">
        <button className="modal-close-btn" onClick={handleClose}>×</button>
        
        {step === 'upload' && (
          <div className="modal-step">
            <h2>Process Attendance</h2>
            <p className="step-description">
              Upload a video of your classroom. Our AI will detect and recognize enrolled students.
            </p>
            
            <div className="upload-area">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                id="video-upload"
                className="file-input"
              />
              <label htmlFor="video-upload" className="file-label">
                {videoFile ? (
                  <div className="file-selected">
                    <span className="file-icon">📹</span>
                    <span className="file-name">{videoFile.name}</span>
                    <span className="file-size">{(videoFile.size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                ) : (
                  <div className="file-placeholder">
                    <span className="file-icon">📁</span>
                    <span>Click to select video or drag and drop</span>
                    <span className="file-hint">MP4, AVI, MOV, MKV (max 500MB)</span>
                  </div>
                )}
              </label>
            </div>

            {error && <div className="form-error">{error}</div>}

            <div className="upload-tips">
              <h4>Tips for best results:</h4>
              <ul>
                <li>Record 10-30 seconds of video</li>
                <li>Slowly pan across the classroom</li>
                <li>Ensure good lighting</li>
                <li>Students should face the camera briefly</li>
              </ul>
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={handleClose}>Cancel</button>
              <button 
                className="btn-primary" 
                onClick={handleProcess}
                disabled={!videoFile}
              >
                Process Video
              </button>
            </div>
          </div>
        )}

        {step === 'processing' && (
          <div className="modal-step center">
            <div className="processing-animation">
              <div className="spinner"></div>
            </div>
            <h2>Processing Video...</h2>
            <p>This may take a few minutes depending on video length</p>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
            <span className="progress-text">{progress}%</span>
          </div>
        )}

        {step === 'results' && session && (
          <div className="modal-step results">
            <h2>Attendance Results</h2>
            <p className="results-date">{formatDate(session.processed_at)}</p>
            
            <div className="results-summary">
              <div className="summary-card present">
                <span className="summary-number">{session.total_students_present}</span>
                <span className="summary-label">Present</span>
              </div>
              <div className="summary-card absent">
                <span className="summary-number">{session.total_students_absent}</span>
                <span className="summary-label">Absent</span>
              </div>
              {session.processing_time_seconds && (
                <div className="summary-card time">
                  <span className="summary-number">{formatDuration(session.processing_time_seconds)}</span>
                  <span className="summary-label">Processing Time</span>
                </div>
              )}
            </div>

            <div className="results-table-container">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Student</th>
                    <th>ID</th>
                    <th>Confidence</th>
                    <th>Frames</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.id} className={record.is_present ? 'present' : 'absent'}>
                      <td>
                        <span className={`status-badge ${record.is_present ? 'present' : 'absent'}`}>
                          {record.is_present ? '✓' : '✗'}
                        </span>
                      </td>
                      <td>{record.student_name}</td>
                      <td>{record.student_id}</td>
                      <td>
                        {record.is_present && record.confidence_score 
                          ? `${(record.confidence_score * 100).toFixed(1)}%` 
                          : '-'}
                      </td>
                      <td>
                        {record.is_present 
                          ? `${record.frames_detected}/${record.frames_total}` 
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={reset}>Process Another</button>
              <button className="btn-primary" onClick={handleClose}>Done</button>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div className="modal-step center">
            <div className="error-icon">✗</div>
            <h2>Processing Failed</h2>
            <p className="error-message">{error}</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={handleClose}>Close</button>
              <button className="btn-primary" onClick={reset}>Try Again</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
