import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Camera as CameraIcon, Fingerprint, Loader2, Upload, CheckCircle2, TriangleAlert } from 'lucide-react'
import { Capacitor } from '@capacitor/core'
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera'
import { checkFingerprintQuality, enrollFingerprint } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'
import ProfileMappingDiagram from '../../components/profile/ProfileMappingDiagram'
import StatTile from '../../components/common/StatTile'
import type { EnrollResponse, FingerprintScanSummary } from '../../types/profile'

function base64ToBlob(base64: string, mimeType: string): Blob {
  const bytes = atob(base64)
  const array = new Uint8Array(bytes.length)
  for (let i = 0; i < bytes.length; i++) array[i] = bytes.charCodeAt(i)
  return new Blob([array], { type: mimeType })
}

const FINGER_OPTIONS = [
  'left_thumb', 'left_index', 'left_middle', 'left_ring', 'left_pinky',
  'right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_pinky',
]

const STAGES = ['Scanning fingerprint', 'Extracting features', 'Building profile', 'Loading virtual brain'] as const

const AUTO_ADVANCE_MS = 2200

export default function Enroll() {
  const { setProfileId } = useProfileId()
  const navigate = useNavigate()

  const [fingerLabel, setFingerLabel] = useState('right_index')
  const [consent, setConsent] = useState(false)
  const [file, setFile] = useState<Blob | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const [checking, setChecking] = useState(false)
  const [scan, setScan] = useState<FingerprintScanSummary | null>(null)

  const [enrolling, setEnrolling] = useState(false)
  const [stageIndex, setStageIndex] = useState(-1)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EnrollResponse | null>(null)
  const [enrolledCount, setEnrolledCount] = useState(0)

  const [cameraOpen, setCameraOpen] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [autoAdvance, setAutoAdvance] = useState(true)

  useEffect(() => {
    if (!result || !autoAdvance) return
    const timer = setTimeout(() => navigate('/profile'), AUTO_ADVANCE_MS)
    return () => clearTimeout(timer)
  }, [result, autoAdvance, navigate])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function pickFile(f: Blob) {
    setFile(f)
    setScan(null)
    setResult(null)
    setError(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(URL.createObjectURL(f))

    setChecking(true)
    try {
      const res = await checkFingerprintQuality(f)
      setScan(res.scan)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read this image.')
    } finally {
      setChecking(false)
    }
  }

  /** In the native Capacitor shell, use the platform camera plugin -- it
   * hands off to the OS's own camera app and returns a photo directly,
   * which is more reliable on-device than a live getUserMedia preview
   * inside a WebView. In a regular browser (including installed-as-PWA),
   * fall back to getUserMedia and an in-page live preview. */
  async function openCamera() {
    setError(null)

    if (Capacitor.isNativePlatform()) {
      try {
        const photo = await Camera.getPhoto({
          resultType: CameraResultType.Base64,
          source: CameraSource.Camera,
          quality: 90,
        })
        if (photo.base64String) {
          void pickFile(base64ToBlob(photo.base64String, `image/${photo.format || 'jpeg'}`))
        }
      } catch {
        // User cancelled the native camera sheet, or permission was denied --
        // not necessarily an error worth surfacing.
      }
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      setCameraOpen(true)
      // videoRef isn't mounted until the next render (cameraOpen just flipped) -
      // attach on the following microtask.
      setTimeout(() => {
        if (videoRef.current) videoRef.current.srcObject = stream
      }, 0)
    } catch {
      setError('Camera unavailable - your browser or device denied camera access. Use file upload instead.')
    }
  }

  function closeCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setCameraOpen(false)
  }

  function capturePhoto() {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      if (blob) void pickFile(blob)
    }, 'image/png')
    closeCamera()
  }

  async function handleEnroll() {
    if (!file || !consent) return
    setEnrolling(true)
    setError(null)
    setStageIndex(0)
    const timers = STAGES.map((_, i) => setTimeout(() => setStageIndex(i), i * 550))
    try {
      const res = await enrollFingerprint(file, fingerLabel, consent)
      setResult(res)
      setProfileId(res.profile_id)
      setEnrolledCount((c) => c + 1)
      setStageIndex(STAGES.length)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enrollment failed.')
      timers.forEach(clearTimeout)
      setStageIndex(-1)
    } finally {
      setEnrolling(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <Fingerprint size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Scan Fingerprint</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Upload a fingerprint image, or use your camera. The image is processed to identify or create your
          Individual Computational Profile - a personalization key, not a biological reading (see Privacy).
        </p>

        <div className="flex flex-wrap gap-3">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-panel-border bg-panel-light px-4 py-2 text-sm text-ink-secondary transition-colors hover:border-cyan-accent/30 hover:text-ink-primary">
            <Upload size={15} strokeWidth={1.75} />
            Upload image
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void pickFile(f)
              }}
            />
          </label>
          <button
            type="button"
            onClick={cameraOpen ? closeCamera : openCamera}
            className="flex items-center gap-2 rounded-lg border border-panel-border bg-panel-light px-4 py-2 text-sm text-ink-secondary transition-colors hover:border-cyan-accent/30 hover:text-ink-primary"
          >
            <CameraIcon size={15} strokeWidth={1.75} />
            {cameraOpen ? 'Close camera' : 'Use camera'}
          </button>
        </div>

        {cameraOpen ? (
          <div className="mt-4 flex flex-col items-start gap-3">
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video ref={videoRef} autoPlay playsInline muted className="w-full max-w-sm rounded-lg border border-panel-border" />
            <button
              type="button"
              onClick={capturePhoto}
              className="flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent hover:bg-cyan-accent/20"
            >
              <CameraIcon size={15} strokeWidth={1.75} />
              Capture
            </button>
          </div>
        ) : null}

        {previewUrl ? (
          <div className="mt-4 flex items-start gap-4">
            <img src={previewUrl} alt="Selected fingerprint" className="h-28 w-28 rounded-lg border border-panel-border object-cover" />
            <div className="flex-1">
              {checking ? (
                <p className="flex items-center gap-2 text-sm text-ink-muted">
                  <Loader2 size={14} className="animate-spin" /> Assessing image quality…
                </p>
              ) : scan ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <StatTile label="Image quality" value={scan.quality.quality_label} />
                  <StatTile label="Ridge visibility" value={`${scan.quality.ridge_visibility_pct}%`} />
                  <StatTile label="Minutiae detected" value={scan.quality.minutiae_detected} />
                  <StatTile label="Orientation confidence" value={`${scan.quality.orientation_confidence_pct}%`} />
                  <StatTile label="Pattern" value={scan.pattern} />
                  <StatTile label="Pattern confidence" value={`${Math.round(scan.pattern_confidence * 100)}%`} />
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        {scan ? <p className="mt-3 text-[11px] text-ink-muted">{scan.measurement_note}</p> : null}
      </div>

      <div className="glass-panel p-6">
        <h2 className="section-label mb-3">Finger &amp; consent</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="section-label mb-1.5 block">Finger</label>
            <select
              value={fingerLabel}
              onChange={(e) => setFingerLabel(e.target.value)}
              className="rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none focus:border-cyan-accent/40"
            >
              {FINGER_OPTIONS.map((f) => (
                <option key={f} value={f}>
                  {f.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-2 pb-1.5 text-xs text-ink-secondary">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="h-3.5 w-3.5 accent-cyan-accent"
            />
            I consent to processing this fingerprint image to create a personalization template. The raw image is
            never stored - only an encrypted numeric template. See{' '}
            <Link to="/profile/privacy" className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2">
              Privacy
            </Link>
            .
          </label>

          <button
            type="button"
            disabled={!file || !consent || enrolling}
            onClick={handleEnroll}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {enrolling ? <Loader2 size={15} className="animate-spin" /> : <Fingerprint size={15} />}
            Build Individual Computational Profile
          </button>
        </div>

        {error ? (
          <p className="mt-3 flex items-center gap-2 text-sm text-status-warning">
            <TriangleAlert size={15} /> {error}
          </p>
        ) : null}

        {stageIndex >= 0 && stageIndex < STAGES.length ? (
          <div className="mt-4 flex flex-col gap-1.5">
            {STAGES.map((label, i) => (
              <p key={label} className={`text-sm ${i <= stageIndex ? 'text-cyan-accent' : 'text-ink-muted'}`}>
                {i < stageIndex ? '✓' : i === stageIndex ? '…' : '·'} {label}
              </p>
            ))}
          </div>
        ) : null}
      </div>

      {result ? (
        <div className="glass-panel flex flex-col items-center gap-4 p-6 text-center">
          <CheckCircle2 size={28} className="text-status-good" />
          <h2 className="text-lg font-semibold text-ink-primary">Your Individual Computational Profile</h2>
          <p className="max-w-md text-sm text-ink-secondary">
            {result.matched_existing_profile
              ? `This fingerprint matched an existing profile (similarity ${Math.round(result.match_similarity * 100)}%). ${enrolledCount > 0 ? 'One more enrollment was added to it.' : ''}`
              : 'A new profile was created with neutral (0.5) computational parameters - nothing is assumed from your fingerprint morphology.'}
          </p>
          <ProfileMappingDiagram />
          <div className="flex items-center gap-3">
            <Link
              to="/profile"
              className="flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent hover:bg-cyan-accent/20"
            >
              Go to Overview now
            </Link>
            {autoAdvance ? (
              <button
                type="button"
                onClick={() => setAutoAdvance(false)}
                className="text-xs text-ink-muted underline decoration-ink-muted/40 underline-offset-2 hover:text-ink-secondary"
              >
                taking you there automatically - stay here instead?
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
