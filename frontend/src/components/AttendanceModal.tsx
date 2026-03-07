import { useState, useRef, useEffect, useCallback } from 'react'
import './AttendanceModal.css'
import { api, type AttendanceRecord, type AttendanceSession } from '../lib/api'

interface AttendanceModalProps {
  isOpen: boolean
  onClose: () => void
  courseId: string
  teacherId: string
}

type Step = 'upload' | 'processing' | 'results' | 'error'
type InputMode = 'upload' | 'record'

export function AttendanceModal({ isOpen, onClose, courseId, teacherId }: AttendanceModalProps) {
  const [step, setStep] = useState<Step>('upload')
  const [inputMode, setInputMode] = useState<InputMode>('upload')
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [error, setError] = useState<string>('')
  const [session, setSession] = useState<AttendanceSession | null>(null)
  const [records, setRecords] = useState<AttendanceRecord[]>([])
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Recording state
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordedUrl, setRecordedUrl] = useState<string>('')
  const [recordingTime, setRecordingTime] = useState(0)
  const videoPreviewRef = useRef<HTMLVideoElement>(null)
  const recordedVideoRef = useRef<HTMLVideoElement>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Clean up camera stream and timer on unmount or modal close
  useEffect(() => {
    return () => {
      stopCamera()
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // Attach stream to video element when stream changes
  useEffect(() => {
    if (videoPreviewRef.current && stream) {
      videoPreviewRef.current.srcObject = stream
    }
  }, [stream])

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    setMediaRecorder(null)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [stream, mediaRecorder])

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      })
      setStream(mediaStream)
      setError('')
    } catch {
      setError('Could not access camera. Please allow camera permissions and ensure no other app is using the camera.')
    }
  }

  const startRecording = async () => {
    if (!stream) {
      await startCamera()
      // Wait for stream to be available
      return
    }

    chunksRef.current = []
    setRecordedBlob(null)
    setRecordedUrl('')
    setRecordingTime(0)

    // Determine supported MIME type
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
        ? 'video/webm;codecs=vp8'
        : 'video/webm'

    try {
      const recorder = new MediaRecorder(stream, { mimeType })

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        setRecordedBlob(blob)
        const url = URL.createObjectURL(blob)
        setRecordedUrl(url)

        // Create a File object from the blob for the API
        const file = new File([blob], `recording_${Date.now()}.webm`, { type: mimeType })
        setVideoFile(file)

        // Stop the timer
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }
      }

      recorder.start(1000) // collect data every second
      setMediaRecorder(recorder)
      setIsRecording(true)

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)
    } catch (err) {
      setError('Failed to start recording. Your browser may not support video recording.')
    }
  }

  // Auto-start recording once camera stream is ready
  useEffect(() => {
    if (stream && !isRecording && !recordedBlob && inputMode === 'record' && !mediaRecorder) {
      // Stream just became available, start recording
      startRecording()
    }
  }, [stream])

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    setIsRecording(false)

    // Stop camera
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
  }

  const handleReRecord = () => {
    setRecordedBlob(null)
    if (recordedUrl) {
      URL.revokeObjectURL(recordedUrl)
    }
    setRecordedUrl('')
    setVideoFile(null)
    setRecordingTime(0)
    setIsRecording(false)
    setMediaRecorder(null)
    startCamera()
  }

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
      setError('Please select or record a video')
      return
    }

    setStep('processing')
    setError('')
    setProgress(0)

    try {
      // Upload video — backend returns job_id immediately
      const response = await api.processAttendance(courseId, teacherId, videoFile)

      if (response.error) {
        setError(response.error)
        setStep('error')
        return
      }

      const jobId = response.data?.job_id
      if (!jobId) {
        setError('No job ID returned')
        setStep('error')
        return
      }

      // Poll for real progress
      const pollInterval = setInterval(async () => {
        try {
          const progressRes = await api.getProcessingProgress(jobId)
          const job = progressRes.data

          if (!job) {
            clearInterval(pollInterval)
            setError('Failed to get processing status')
            setStep('error')
            return
          }

          setProgress(Math.round(job.progress * 100))

          if (job.status === 'completed' && job.session_id) {
            clearInterval(pollInterval)

            const sessionResponse = await api.getAttendanceSession(job.session_id)
            if (sessionResponse.data) {
              setSession(sessionResponse.data.session)
              setRecords(sessionResponse.data.records)
              setStep('results')
            } else {
              setError('Failed to fetch attendance results')
              setStep('error')
            }
          } else if (job.status === 'error') {
            clearInterval(pollInterval)
            setError(job.error || 'Processing failed')
            setStep('error')
          }
        } catch {
          clearInterval(pollInterval)
          setError('Lost connection while processing')
          setStep('error')
        }
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setStep('error')
    }
  }

  const switchInputMode = (mode: InputMode) => {
    if (mode === inputMode) return

    // Clean up current mode state
    if (inputMode === 'record') {
      stopCamera()
      if (recordedUrl) URL.revokeObjectURL(recordedUrl)
      setRecordedBlob(null)
      setRecordedUrl('')
      setIsRecording(false)
      setRecordingTime(0)
    }

    setVideoFile(null)
    setError('')
    setInputMode(mode)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const reset = () => {
    setStep('upload')
    setInputMode('upload')
    setVideoFile(null)
    setError('')
    setSession(null)
    setRecords([])
    setProgress(0)
    stopCamera()
    if (recordedUrl) URL.revokeObjectURL(recordedUrl)
    setRecordedBlob(null)
    setRecordedUrl('')
    setIsRecording(false)
    setRecordingTime(0)
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

  const formatRecordingTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
    const secs = (seconds % 60).toString().padStart(2, '0')
    return `${mins}:${secs}`
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
              Upload or record a video of your classroom. Our AI will detect and recognize enrolled students.
            </p>

            {/* Tab selector */}
            <div className="input-mode-tabs">
              <button
                className={`tab-btn ${inputMode === 'upload' ? 'active' : ''}`}
                onClick={() => switchInputMode('upload')}
              >
                <span className="tab-icon">📁</span>
                Upload Video
              </button>
              <button
                className={`tab-btn ${inputMode === 'record' ? 'active' : ''}`}
                onClick={() => switchInputMode('record')}
              >
                <span className="tab-icon">🎥</span>
                Record Video
              </button>
            </div>

            {/* Upload mode */}
            {inputMode === 'upload' && (
              <>
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

                <div className="upload-tips">
                  <h4>Tips for best results:</h4>
                  <ul>
                    <li>Record 10-30 seconds of video</li>
                    <li>Slowly pan across the classroom</li>
                    <li>Ensure good lighting</li>
                    <li>Students should face the camera briefly</li>
                  </ul>
                </div>
              </>
            )}

            {/* Record mode */}
            {inputMode === 'record' && (
              <div className="record-section">
                {!recordedBlob ? (
                  <>
                    {/* Camera preview / pre-record state */}
                    <div className="record-camera-container">
                      {stream ? (
                        <video
                          ref={videoPreviewRef}
                          autoPlay
                          playsInline
                          muted
                          className="record-video-preview"
                        />
                      ) : (
                        <div className="record-placeholder">
                          <span className="record-placeholder-icon">🎥</span>
                          <span>Click "Start Recording" to begin</span>
                        </div>
                      )}

                      {isRecording && (
                        <div className="recording-overlay">
                          <div className="recording-timer">
                            <span className="recording-dot"></span>
                            <span className="recording-time">{formatRecordingTime(recordingTime)}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="record-controls">
                      {!isRecording && !stream && (
                        <button
                          className="record-btn start-btn"
                          onClick={startCamera}
                        >
                          <span className="btn-icon">⏺</span>
                          Start Recording
                        </button>
                      )}
                      {isRecording && (
                        <button
                          className="record-btn stop-btn"
                          onClick={stopRecording}
                        >
                          <span className="btn-icon">⏹</span>
                          Stop Recording
                        </button>
                      )}
                    </div>

                    <div className="upload-tips">
                      <h4>Recording tips:</h4>
                      <ul>
                        <li>Record 10-30 seconds</li>
                        <li>Slowly pan across the classroom</li>
                        <li>Ensure good lighting conditions</li>
                        <li>Students should face the camera briefly</li>
                      </ul>
                    </div>
                  </>
                ) : (
                  <>
                    {/* Recorded preview */}
                    <div className="recorded-preview">
                      <div className="recorded-header">
                        <span className="recorded-badge">✓ Video Recorded</span>
                        <span className="recorded-duration">{formatRecordingTime(recordingTime)}</span>
                      </div>
                      <video
                        ref={recordedVideoRef}
                        src={recordedUrl}
                        controls
                        className="recorded-video"
                      />
                      <div className="recorded-info">
                        <span className="file-size">
                          {videoFile && `${(videoFile.size / 1024 / 1024).toFixed(2)} MB`}
                        </span>
                      </div>
                    </div>
                    <div className="record-controls">
                      <button
                        className="record-btn rerecord-btn"
                        onClick={handleReRecord}
                      >
                        <span className="btn-icon">🔄</span>
                        Re-record
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {error && <div className="form-error">{error}</div>}

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
