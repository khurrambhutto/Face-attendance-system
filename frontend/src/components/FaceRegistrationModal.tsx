import { useState, useRef, useCallback, useEffect } from 'react'
import './FaceRegistrationModal.css'
import { api } from '../lib/api'

interface FaceRegistrationModalProps {
  isOpen: boolean
  onClose: () => void
  userId: string
}

type Step = 'info' | 'capture' | 'saving' | 'success' | 'error'

interface CapturedPhoto {
  id: string
  imageData: string
  blob: Blob
  timestamp: string
}

export function FaceRegistrationModal({ isOpen, onClose, userId }: FaceRegistrationModalProps) {
  const [step, setStep] = useState<Step>('info')
  const [studentId, setStudentId] = useState('')
  const [studentName, setStudentName] = useState('')
  const [capturedPhotos, setCapturedPhotos] = useState<CapturedPhoto[]>([])
  const [isCapturing, setIsCapturing] = useState(false)
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false)
  const [error, setError] = useState<string>('')
  const [stream, setStream] = useState<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (step === 'capture' && !stream) {
      startCamera()
    }
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [step, stream])

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false 
      })
      setStream(mediaStream)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch {
      setError('Could not access camera. Please allow camera permissions.')
      setStep('error')
    }
  }

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || capturedPhotos.length >= 3) return

    setIsCapturing(true)
    
    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')
    
    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    
    canvas.toBlob((blob) => {
      if (blob) {
        const imageData = canvas.toDataURL('image/jpeg', 0.9)
        
        const newPhoto: CapturedPhoto = {
          id: crypto.randomUUID(),
          imageData,
          blob,
          timestamp: new Date().toISOString()
        }

        setCapturedPhotos(prev => [...prev, newPhoto])
      }
      setIsCapturing(false)
    }, 'image/jpeg', 0.9)
  }, [capturedPhotos.length])

  const removePhoto = (id: string) => {
    setCapturedPhotos(prev => prev.filter(p => p.id !== id))
  }

  const handleStartCapture = async () => {
    const trimmedId = studentId.trim()
    const trimmedName = studentName.trim()

    if (!trimmedId || !trimmedName) {
      setError('Please enter both Student ID and Name')
      return
    }

    setIsCheckingDuplicate(true)
    setError('')

    try {
      const response = await api.checkEnrollment(trimmedId, trimmedName)

      if (response.error) {
        setError(response.error)
        setIsCheckingDuplicate(false)
        return
      }

      if (response.data?.exists) {
        if (response.data.duplicate_id) {
          setError(`Student ID "${trimmedId}" is already registered. Please use a different ID.`)
        } else if (response.data.duplicate_name) {
          setError(`Name "${trimmedName}" is already enrolled. Please contact your teacher if this is an error.`)
        }
        setIsCheckingDuplicate(false)
        return
      }

      setStep('capture')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify enrollment. Please try again.')
    } finally {
      setIsCheckingDuplicate(false)
    }
  }

  const handleSave = async () => {
    if (capturedPhotos.length < 3) {
      setError('Please capture all 3 photos')
      return
    }

    setStep('saving')
    setError('')

    try {
      const blobs = capturedPhotos.map(photo => photo.blob)
      
      const response = await api.registerEnrollment(
        userId,
        studentId.trim(),
        studentName.trim(),
        blobs
      )

      if (response.error) {
        setError(response.error)
        setStep('error')
        return
      }

      if (response.data?.success) {
        setStep('success')
      } else {
        setError('Failed to save enrollment')
        setStep('error')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setStep('error')
    }
  }

  const reset = () => {
    setStep('info')
    setStudentId('')
    setStudentName('')
    setCapturedPhotos([])
    setError('')
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
  }

  const handleClose = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    reset()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="face-registration-modal-overlay">
      <div className="face-registration-modal">
        <button className="modal-close-btn" onClick={handleClose}>×</button>
        
        {step === 'info' && (
          <div className="modal-step">
            <h2>Register Your Face</h2>
            <div className="step-indicator">Step 1 of 3</div>
            <p className="step-description">
              Enter your student information below. We'll capture 3 photos of your face for attendance recognition.
            </p>
            
            <div className="student-info-form">
              <div className="form-group">
                <label htmlFor="student-id" className="form-label">Student ID</label>
                <input
                  id="student-id"
                  type="text"
                  className="form-input"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  placeholder="e.g., 49"
                />
              </div>
              <div className="form-group">
                <label htmlFor="student-name" className="form-label">Full Name</label>
                <input
                  id="student-name"
                  type="text"
                  className="form-input"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="e.g., Khurram"
                />
              </div>
            </div>

            {error && <div className="form-error">{error}</div>}

            <div className="modal-actions">
              <button className="btn-secondary" onClick={handleClose} disabled={isCheckingDuplicate}>Cancel</button>
              <button 
                className="btn-primary" 
                onClick={handleStartCapture}
                disabled={isCheckingDuplicate}
              >
                {isCheckingDuplicate ? 'Checking...' : 'Start Capture'}
              </button>
            </div>
          </div>
        )}

        {step === 'capture' && (
          <div className="modal-step">
            <h2>Capture Photos</h2>
            <div className="step-indicator">Step 2 of 3 - Photo {capturedPhotos.length + 1} of 3</div>
            
            <div className="capture-info-bar">
              <span><strong>ID:</strong> {studentId}</span>
              <span><strong>Name:</strong> {studentName}</span>
            </div>
            
            <div className="camera-container">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted
                className="camera-preview"
              />
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              
              <div className="camera-overlay">
                <div className="face-guide"></div>
                <p className="camera-hint">Center your face in the frame</p>
              </div>
            </div>

            <div className="capture-controls">
              <button 
                className="capture-btn"
                onClick={capturePhoto}
                disabled={isCapturing || capturedPhotos.length >= 3}
              >
                {capturedPhotos.length >= 3 ? 'All Photos Captured' : 'Capture Photo'}
              </button>
            </div>

            {capturedPhotos.length > 0 && (
              <div className="captured-photos">
                <h4>Captured Photos</h4>
                <div className="photos-grid">
                  {capturedPhotos.map((photo, index) => (
                    <div key={photo.id} className="photo-item">
                      <img src={photo.imageData} alt={`Photo ${index + 1}`} />
                      <button 
                        className="remove-photo-btn"
                        onClick={() => removePhoto(photo.id)}
                      >
                        ×
                      </button>
                      <span className="photo-number">{index + 1}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setStep('info')}>Back</button>
              <button 
                className="btn-primary" 
                onClick={handleSave}
                disabled={capturedPhotos.length < 3}
              >
                Save Enrollment
              </button>
            </div>
          </div>
        )}

        {step === 'saving' && (
          <div className="modal-step center">
            <div className="loading-spinner"></div>
            <h2>Saving...</h2>
            <p>Processing your photos and saving to database</p>
          </div>
        )}

        {step === 'success' && (
          <div className="modal-step center">
            <div className="success-icon">✓</div>
            <h2>Enrollment Complete!</h2>
            <p>Your face has been registered successfully.</p>
            <button className="btn-primary" onClick={handleClose}>Done</button>
          </div>
        )}

        {step === 'error' && (
          <div className="modal-step center">
            <div className="error-icon">✗</div>
            <h2>Enrollment Failed</h2>
            <p className="error-message">{error}</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={handleClose}>Cancel</button>
              <button className="btn-primary" onClick={reset}>Try Again</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
